import unicodedata

from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model
from django.utils.encoding import force_unicode
from django.utils.text import slugify

from . import settings as simple_geo_settings


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
    if isinstance(value, str):
        value = force_unicode(value)
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')


def city_slugify(obj, counter=0):
    if counter:
        tmp = u"{0} {1} {2}".format(obj.name, obj.province, counter)
    else:
        tmp = u"{0} {1}".format(obj.name, obj.province)

    tmp = slugify(tmp)
    if obj.slug != tmp:
        if obj.__class__.objects.all().filter(slug=tmp).exists():
            return city_slugify(obj, counter + 1)

    return tmp


