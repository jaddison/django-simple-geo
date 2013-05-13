import unicodedata

from django.contrib.gis.db.models import PointField, GeoManager
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_unicode
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from . import settings as simple_geo_settings


def get_city_model():
    "Return the City model that is active in this project"
    from django.db.models import get_model

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
    from django.db.models import get_model

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


class BaseCity(models.Model):
    name = models.CharField(_(u'name'), max_length=190)
    name_ascii = models.CharField(_(u'ASCII name'), max_length=190)
    slug = models.SlugField(_(u'slug'), max_length=200, unique=True, blank=True)
    province = models.CharField(_(u'state/province'), max_length=3)
    country = models.CharField(_(u'country'), max_length=3)
    point = PointField(_(u'point'), null=True, blank=True)
    updated = models.DateTimeField(_(u"updated"))

    objects = GeoManager()

    class Meta:
        verbose_name = _(u"City")
        verbose_name_plural = _(u"Cities")
        abstract = True

    def __unicode__(self):
        return u"{0}, {1}, {2}".format(self.name, self.province, self.country)

    def save(self, *args, **kwargs):
        self.name_ascii = to_ascii(self.name)
        self.slug = city_slugify(self)
        self.updated = kwargs.pop('last_updated', timezone.now())
        return super(BaseCity, self).save(*args, **kwargs)


if simple_geo_settings.SIMPLE_GEO_CITY_MODEL == 'simple_geo.City':
    class City(BaseCity):
        pass


class BasePostalCode(models.Model):
    city = models.ForeignKey(simple_geo_settings.SIMPLE_GEO_CITY_MODEL, verbose_name=_(u'city'), null=True, blank=True)
    code = models.CharField(_(u'zip/postal code'), max_length=16)
    point = PointField(_(u'point'), null=True, blank=True)
    updated = models.DateTimeField(_(u"updated"))

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"{0}: {1}".format(self.code, self.city)

    def save(self, *args, **kwargs):
        self.updated = kwargs.pop('last_updated', timezone.now())
        return super(BaseCity, self).save(*args, **kwargs)


if simple_geo_settings.SIMPLE_GEO_POSTALCODE_MODEL == 'simple_geo.PostalCode':
    class PostalCode(BasePostalCode):
        objects = GeoManager()

        class Meta:
            verbose_name = _(u"Postal/Zip Code")
            verbose_name_plural = _(u"Postal/Zip Codes")

        def __unicode__(self):
            return u"{0}, {1}".format(self.code, self.city)
