from __future__ import unicode_literals
from django.conf import settings

SIMPLE_GEO_HIDE_ADMIN = getattr(settings, 'SIMPLE_GEO_HIDE_ADMIN', False)
SIMPLE_GEO_CITY_MODEL = getattr(settings, 'SIMPLE_GEO_CITY_MODEL', 'simple_geo.City')
SIMPLE_GEO_POSTALCODE_MODEL = getattr(settings, 'SIMPLE_GEO_POSTALCODE_MODEL', 'simple_geo.PostalCode')
SIMPLE_GEO_GOOGLE_MAPS_API_KEY = getattr(settings, 'SIMPLE_GEO_GOOGLE_MAPS_API_KEY', False)
