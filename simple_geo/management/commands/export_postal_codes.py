from __future__ import unicode_literals
import csv
import re
import datetime

from django.core.management.base import BaseCommand
from django.utils import six

from ...utils import get_postalcode_model

""" This script has only been tested on a PostgreSQL 8.4/PostGIS 2.0 database configuration.

The regex used below to parse the PointField data may be/is likely specific to that
configuration. If anyone knows of a better/generic way to separate the longitude/latitude
while maintaining precision, I'd love to hear about it.
"""


class Command(BaseCommand):
    args = ''
    help = 'Exports postal code data to a CSV file.'


    def handle(self, *args, **options):
        filename = "export-{0}.csv".format(datetime.datetime.now().strftime("%Y%m%d-%H%M"))
        with open(filename, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile)

            # write in the header row
            csvwriter.writerow([
                'code',
                'city',
                'region',
                'country',
                'code_updated',
                'city_updated',
                'code_longitude',
                'code_latitude',
                'city_longitude',
                'city_latitude'
            ])

            point_re = re.compile(r'POINT ?\((-?\d*\.?\d*) (\-?\d*\.?\d*)\)')

            for item in get_postalcode_model().objects.all().select_related('city').values_list(
                'code',
                'city__name',
                'city__province',
                'city__country',
                'updated',
                'city__updated',
                'point',
                'city__point'
            ):
                row = [
                    six.text_type(item[0]).encode('utf-8'),
                    six.text_type(item[1]).encode('utf-8'),
                    six.text_type(item[2]).encode('utf-8'),
                    six.text_type(item[3]).encode('utf-8'),
                    six.text_type(item[4]).encode('utf-8'),
                    six.text_type(item[5]).encode('utf-8'),
                ]
                # if we have point, extract their long/lat values as strings and then insert the proper values in
                # our row; maintain precision of our PointField by not doing any type cast/conversion, just regex
                # out the string values

                # first our postal code point values
                values = ['', '']
                if item[6]:
                    m = point_re.match(six.text_type(item[6]))
                    if m:
                        values = m.groups()

                row += values

                # first our city point values
                values = ['', '']
                if item[7]:
                    m = point_re.match(six.text_type(item[7]))
                    if m:
                        values = m.groups()

                row += values

                print(row)
                csvwriter.writerow(row)
