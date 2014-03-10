from django.contrib.gis.db.models import PointField, GeoManager
from django.contrib.gis.geos import Point
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from . import settings as simple_geo_settings
from .utils import to_ascii, city_slugify, geocode, GeocodingError


class BaseCity(models.Model):
    STATUS_IGNORED = 0
    STATUS_NEW = 1
    STATUS_IMPORTED = 2
    STATUS_INACTIVE = 3
    STATUS_ACTIVE = 4
    STATUS_CHOICES = (
        (STATUS_IGNORED, _(u"Ignored")),
        (STATUS_NEW, _(u"New")),
        (STATUS_IMPORTED, _(u"Imported")),
        (STATUS_INACTIVE, _(u"Inactive")),
        (STATUS_ACTIVE, _(u"Active")),
    )

    name = models.CharField(_(u'name'), max_length=190)
    name_ascii = models.CharField(_(u'ASCII name'), max_length=190, db_index=True)
    slug = models.SlugField(_(u'slug'), max_length=200, unique=True, blank=True)
    province = models.CharField(_(u'state/province'), max_length=3)
    country = models.CharField(_(u'country'), max_length=3)
    point = PointField(_(u'point'), null=True, blank=True)
    updated = models.DateTimeField(_(u"updated"))
    status = models.PositiveSmallIntegerField(_(u'status'), choices=STATUS_CHOICES, default=STATUS_NEW)

    objects = GeoManager()

    class Meta:
        verbose_name = _(u"City")
        verbose_name_plural = _(u"Cities")
        abstract = True

    format_slug = u"{name} {province} {country}"
    format_slug_counter = u"{name} {province} {country} {counter}"

    @property
    def province_display(self):
        return self.province

    @property
    def country_display(self):
        return self.country

    def __unicode__(self):
        return u"{0}, {1}, {2}".format(self.name, self.province_display, self.country)

    def save(self, *args, **kwargs):
        self.name_ascii = to_ascii(self.name)
        self.slug = city_slugify(self)
        self.updated = kwargs.pop('last_updated', timezone.now())

        # don't have a coordinate point? let's find one from our geocoder!
        if not self.point:
            try:
                data = geocode(country=self.country, city=self.name, region=self.province)
            except GeocodingError, e:
                # if we got in here, it's most likely because we're over the daily quota
                data = None

            if data and 'point' in data:
                point = data.get('point', {})
                self.point = Point(point.get('lng'), point.get('lat')) if 'lng' in point else None

        return super(BaseCity, self).save(*args, **kwargs)


class BasePostalCode(models.Model):
    city = models.ForeignKey(simple_geo_settings.SIMPLE_GEO_CITY_MODEL, verbose_name=_(u'city'), null=True, blank=True)
    code = models.CharField(_(u'zip/postal code'), max_length=16, db_index=True)
    point = PointField(_(u'point'), null=True, blank=True)
    updated = models.DateTimeField(_(u"updated"))

    objects = GeoManager()

    class Meta:
        verbose_name = _(u"Postal/Zip Code")
        verbose_name_plural = _(u"Postal/Zip Codes")
        abstract = True

    def __unicode__(self):
        return u"{0}: {1}".format(self.code, self.city)

    def save(self, *args, **kwargs):
        self.updated = kwargs.pop('last_updated', timezone.now())
        return super(BasePostalCode, self).save(*args, **kwargs)


if simple_geo_settings.SIMPLE_GEO_CITY_MODEL == 'simple_geo.City':
    class City(BaseCity):
        pass


if simple_geo_settings.SIMPLE_GEO_POSTALCODE_MODEL == 'simple_geo.PostalCode':
    class PostalCode(BasePostalCode):
        pass
