from __future__ import unicode_literals
import json
import random
import time
import unicodedata

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.text import slugify
import requests

try:
    from django.apps import apps
    get_model = apps.get_model
except ImportError:
    from django.db.models.loading import get_model

from . import settings as simple_geo_settings


class GeocodingError(Exception):
    pass


def get_city_model():
    "Return the City model that is active in this project"
    try:
        app_label, model_name = simple_geo_settings.SIMPLE_GEO_CITY_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("SIMPLE_GEO_CITY_MODEL must be of the form 'app_label.model_name'")
    city_model = get_model(app_label, model_name)
    if city_model is None:
        raise ImproperlyConfigured("SIMPLE_GEO_CITY_MODEL refers to model '%s' that has not been installed" % simple_geo_settings.SIMPLE_GEO_CITY_MODEL)
    return city_model


def get_postalcode_model():
    "Return the PostalCode model that is active in this project"
    try:
        app_label, model_name = simple_geo_settings.SIMPLE_GEO_POSTALCODE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("SIMPLE_GEO_POSTALCODE_MODEL must be of the form 'app_label.model_name'")
    postalcode_model = get_model(app_label, model_name)
    if postalcode_model is None:
        raise ImproperlyConfigured("SIMPLE_GEO_POSTALCODE_MODEL refers to model '%s' that has not been installed" % simple_geo_settings.SIMPLE_GEO_POSTALCODE_MODEL)
    return postalcode_model


def to_ascii(value):
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')


def city_slugify(obj, counter=0):
    tmp = obj.format_slug if not counter else obj.format_slug_counter

    context = {
        'name': obj.name,
        'province': obj.province,
        'country': obj.country,
        'province_display': obj.province_display,
        'country_display': obj.country_display,
        'counter': counter
    }
    tmp = slugify(tmp.format(**context))

    if obj.slug != tmp:
        if obj.__class__.objects.all().filter(slug=tmp).exists():
            return city_slugify(obj, counter + 1)

    return tmp


def geocode(*args, **kwargs):
    # check out https://developers.google.com/maps/documentation/geocoding/#ComponentFiltering for
    # other component filtering elements
    components = []
    if 'code' in kwargs:
        components.append("postal_code:{code}")
    if 'country' in kwargs:
        components.append("country:{country}")
    if 'region' in kwargs:
        components.append("administrative_area:{region}")
    if 'city' in kwargs:
        components.append("locality:{city}")

    # don't want to hammer the API
    wait = kwargs.get('wait', random.uniform(1,3))
    time.sleep(wait)

    # get rid of leading/trailing spaces in component values
    component_params = dict([(k,v.strip()) for k,v in six.iteritems(kwargs)])
    query_params = {
        'sensor': 'false',
        'address': kwargs.get('address', '').strip(),
        'components': ("|".join(components)).format(**component_params)
    }
    url = "http://maps.googleapis.com/maps/api/geocode/json"
    response = requests.get(url, params=query_params)

    address_data = {}
    if response.status_code == requests.codes.ok:
        result = json.loads(response.text)

        status = result.get('status', '')
        if status not in ('OK', 'ZERO_RESULTS'):
            raise GeocodingError("Geocoding error: {0}".format(status))

        result = result.get('results', [])
        if not result:
            return address_data

        result = result[0] if len(result) else {}
        coordinate = result.get('geometry', {}).get('location')
        if coordinate:
            address_data['point'] = coordinate
        viewport = result.get('geometry', {}).get('viewport')
        if viewport:
            address_data['viewport'] = viewport
        for item in result.get('address_components', []):
            types = item.get('types', [])
            type = None
            for type in types:
                if type == 'political':
                    continue
                break

            if type in [
                'postal_code',
                'locality',
                'sublocality',
                'administrative_area_level_1',
                'administrative_area_level_2',
                'administrative_area_level_3',
                'country'
            ]:
                address_data[type] = item.get('short_name', '')

    return address_data
