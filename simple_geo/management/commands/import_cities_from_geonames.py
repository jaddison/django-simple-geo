from __future__ import unicode_literals
import sys
import csv
from optparse import make_option
import os
import datetime

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError

from ...utils import get_city_model


region_code_map = {
    'CA.01': 'AB',
    'CA.02': 'BC',
    'CA.03': 'MB',
    'CA.04': 'NB',
    'CA.05': 'NL',
    'CA.07': 'NS',
    'CA.08': 'ON',
    'CA.09': 'PE',
    'CA.10': 'QC',
    'CA.11': 'SK',
    'CA.12': 'YT',
    'CA.13': 'NT',
    'CA.14': 'NU'
}


class Command(BaseCommand):
    args = 'CA.txt'
    help = 'Imports cities from a GEONames formatted city file - eg. CA.txt'
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

    def get_or_create_city(self, name, region, country, last_updated, point=None):
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
                if point and last_updated and (city.updated < last_updated) and (not city.point or city.point != point):
                    city.point = point
                    city.save()
                    self.updated_cities += 1
                    print('and updated',)

            except get_city_model().DoesNotExist:
                city = get_city_model()(
                    name=name,
                    province=region,
                    country=country,
                    point=point,
                    status=get_city_model().STATUS_IMPORTED
                )
                city.save(last_updated=last_updated)
                self.created_cities += 1
                print('created',)

            print(city)

        return city

    def handle(self, *args, **options):
        if not len(args):
            raise CommandError("You must pass in a CSV file to import.")

        self.rows_processed = 0
        self.created_cities = 0
        self.updated_cities = 0

        self.restrict_country = options.get('country').upper()
        self.restrict_regions = options.get('regions', [])
        if self.restrict_regions:
            self.restrict_regions = self.restrict_regions.upper().split(',')

        csv.field_size_limit(sys.maxsize)

        # iterate through the filenames listed in the argument list
        for filename in args:
            if os.path.isdir(filename):
                continue

            with open(filename, 'rU') as csvfile:
                data = csv.reader(csvfile, delimiter='\t')

                for index, row in enumerate(data):
                    country = row[8].strip().upper()
                    # make sure we get province abbreviations rather than geonames' numerical format
                    region = row[10].strip().upper()
                    region = region_code_map.get("{0}.{1}".format(country, region), region)

                    # don't process items we're trying to avoid for now...
                    if country and self.restrict_country and country != self.restrict_country:
                        continue
                    if region and self.restrict_regions and region not in self.restrict_regions:
                        continue

                    # we only want populated items (towns and cities), denoted by PPL*; see
                    # http://www.geonames.org/export/codes.html
                    row_type = row[7].upper()
                    if row_type not in ['PPL', 'PPLC', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4']:
                        continue

                    # do our best to clean up the city - it should be already be good
                    city = " ".join(row[1].decode('utf-8').strip().split(' '))

                    # let's get our coordinate/point, if available
                    latitude = row[4].strip()
                    longitude = row[5].strip()
                    city_point = Point(float(longitude), float(latitude)) if (latitude and longitude) else None

                    # this is when this record was last updated by geonames
                    last_updated = datetime.datetime.strptime(row[18], '%Y-%m-%d')

                    # print(row_type, country, region, city, latitude, longitude, city_point)

                    # get or create the city associate with this row
                    self.get_or_create_city(city, region, country, last_updated, city_point)
                    # if index > 1000:
                    #     break

                self.rows_processed += index + 1

        print("{0} new cities created, {1} cities updated. {2} rows processed.".format(self.created_cities, self.updated_cities, self.rows_processed))