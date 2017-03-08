from __future__ import unicode_literals
import csv
from optparse import make_option
import os

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.utils import six

from ...utils import get_postalcode_model, get_city_model, geocode, GeocodingError


class Command(BaseCommand):
    args = 'postal_code_data.csv'
    help = 'Imports postal code data into the database from a specifically-formatted CSV file'
    option_list = BaseCommand.option_list + (
        make_option(
            '--regions',
            action='store',
            type='string',
            dest='regions',
            default='',
            help='Comma separated list of regions (2 letter state/province codes) to process.'
        ),
        make_option(
            '--country',
            action='store',
            type='string',
            dest='country',
            default='',
            help='A single 2 letter country code used to restrict processing.'
        )
    )

    def get_or_create_city(self, name, region, country, point=None):
        # let's get or create our city - not using get_or_create() because we want
        # to do a case insensitive match on the name (__iexact)
        city = None
        if name and region and country:
            try:
                city = get_city_model().objects.get(
                    name__iexact=name,
                    province=region,
                    country=country
                )
                print('retrieved',)
            except get_city_model().DoesNotExist:
                city = get_city_model().objects.create(
                    name=name,
                    province=region,
                    country=country,
                    point=point if point else None,
                    status=get_city_model().STATUS_IMPORTED
                )
                self.created_cities += 1
                print('created',)

            print(city)

        return city

    def handle(self, *args, **options):
        if not len(args):
            raise CommandError("You must pass in a CSV file to import.")

        self.rows_processed = 0
        self.created_postal_codes = 0
        self.created_cities = 0
        self.updated_postal_codes = 0
        self.updated_cities = 0

        self.restrict_country = options.get('country').upper()
        self.restrict_regions = options.get('regions', [])
        if self.restrict_regions:
            self.restrict_regions = self.restrict_regions.upper().split(',')

        # iterate through the filenames listed in the argument list
        for filename in args:
            if os.path.isdir(filename):
                continue

            with open(filename, 'rU') as csvfile:
                data = csv.reader(csvfile)

                header_row = None
                row_code = None
                row_city = None
                row_region = None
                row_country = None
                row_code_updated = None
                row_city_updated = None
                row_code_latitude = None
                row_code_longitude = None
                row_city_latitude = None
                row_city_longitude = None

                for index, row in enumerate(data):
                    if index == 0:
                        header_row = row
                        for colindex, column in enumerate(header_row):
                            if column.lower() == 'code':
                                row_code = colindex
                            elif column.lower() == 'city':
                                row_city = colindex
                            elif column.lower() == 'country':
                                row_country = colindex
                            elif column.lower() == 'region':
                                row_region = colindex
                            elif column.lower() == 'code_updated':
                                row_code_updated = colindex
                            elif column.lower() == 'city_updated':
                                row_city_updated = colindex
                            elif column.lower() == 'code_latitude':
                                row_code_latitude = colindex
                            elif column.lower() == 'code_longitude':
                                row_code_longitude = colindex
                            elif column.lower() == 'city_latitude':
                                row_city_latitude = colindex
                            elif column.lower() == 'city_longitude':
                                row_city_longitude = colindex

                        if row_country is None or row_code is None:
                            raise CommandError("The first row in the file must label both 'country' and 'code' columms. The 'region' column is optional, representing state/province.")

                        # we've got our column definitions from the first row, so let's proceed to the next row (the first data row)
                        continue


                    code = ''
                    city = ''
                    region = ''
                    country = ''
                    code_updated = None
                    city_updated = None
                    code_point = None
                    city_point = None

                    if row_code is not None:
                        code = "".join("".join(row[row_code].strip().upper().split(' ')).split('-'))
                    if row_city is not None:
                        city = " ".join(row[row_city].strip().split(' '))
                    if row_region is not None:
                        region = row[row_region].upper()
                    if row_country is not None:
                        country = row[row_country].upper()
                    if row_code_updated is not None:
                        code_updated = row[row_code_updated]
                    if row_city_updated is not None:
                        city_updated = row[row_city_updated]
                    if None not in (row_code_longitude, row_code_latitude):
                        code_point = Point(float(row[row_code_longitude]), float(row[row_code_latitude]))
                    if None not in (row_city_longitude, row_city_latitude):
                        city_point = Point(float(row[row_city_longitude]), float(row[row_city_latitude]))

                    # don't process items we're trying to avoid for now...
                    if country and self.restrict_country and country != self.restrict_country:
                        continue
                    if region and self.restrict_regions and region not in self.restrict_regions:
                        continue

                    # let's get a matching postal code, if available!
                    postal_code_obj = None
                    if code:
                        qs_base = get_postalcode_model().objects.all().select_related('city')
                        qs = qs_base.filter(city__country=country)

                        try:
                            postal_code_obj = qs.get(code=code)
                        except get_postalcode_model().DoesNotExist:
                            # possible there isn't a city set on the postal code
                            try:
                                postal_code_obj = qs_base.get(code=code)
                            except get_postalcode_model().MultipleObjectsReturned:
                                raise
                            except get_postalcode_model().DoesNotExist:
                                pass

                    # get or create the city associate with this row
                    city_obj = self.get_or_create_city(city, region, country, city_point)
                    if city_point and city_obj and (not city_obj.point or city_obj.point != city_point):
                        city_obj.point = city_point
                        city_obj.save()
                        self.updated_cities += 1
                        print('city update:', city_obj)

                    if postal_code_obj:
                        # already have a postal code object, let's just verify what's in it is up to date
                        changed_postal = False
                        # if the city isn't set, or the city is different, then change it
                        if city_obj and postal_code_obj.city_id != city_obj.id:
                            postal_code_obj.city = city_obj
                            changed_postal = True
                            print('postal code update, city:', postal_code_obj)

                        if code_point and (not postal_code_obj.point or postal_code_obj.point != code_point):
                            postal_code_obj.point = code_point
                            changed_postal = True
                            print('postal code update, point:', postal_code_obj)

                        if changed_postal:
                            postal_code_obj.save()
                            self.updated_postal_codes += 1
                    elif code:
                        # we have a code and a city, but no postal code object retrieved, we must need to create!
                        if code_point and city_obj:
                            # if we have a postal code point coordinate, then just create the postal code item
                            # without geocoding it
                            postal_code_obj = get_postalcode_model().objects.create(
                                city=city_obj,
                                code=code,
                                point=code_point
                            )
                            print('postal code created, no geocoding:', postal_code_obj)
                        else:
                            try:
                                address_data = geocode(city=city, region=region, country=country, code=code)
                            except GeocodingError as e:
                                # if we got in here, it's most likely because we're over the daily quota
                                print(six.text_type(e))
                                break
                            
                            if not address_data:
                                continue

                            # if we did this level of fallbacks, we'd probably end up with a lot of county
                            # names in the city field, for example. We'll have to deal with City=None cases
                            # manually.
                            # city_name = address_data.get(
                            #     'locality',
                            #     address_data.get(
                            #         'sublocality',
                            #         address_data.get(
                            #             'administrative_area_level_2',
                            #             address_data.get('administrative_area_level_3', '')
                            #         )
                            #     )
                            # )

                            point = address_data.get('point', {})
                            postal_code_obj = get_postalcode_model().objects.create(
                                city=self.get_or_create_city(
                                    address_data.get('locality', address_data.get('sublocality', '')),
                                    address_data.get('administrative_area_level_1', '').upper(),
                                    address_data.get('country', '').upper()
                                ),
                                code=address_data.get('postal_code', ''),
                                point=Point(point.get('lng'), point.get('lat')) if 'lng' in point else None
                            )
                            print('postal code created, with geocoding:', postal_code_obj)
                        self.created_postal_codes += 1

                self.rows_processed += index + 1

        print("{0} new cities created, {1} new postal codes created. {2} rows processed.".format(self.created_cities, self.created_postal_codes, self.rows_processed))