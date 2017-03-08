from __future__ import unicode_literals
from django.contrib.gis.db.models import PointField, GeoManager
from django.contrib.gis.geos import Point
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
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
        (STATUS_IGNORED, _("Ignored")),
        (STATUS_NEW, _("New")),
        (STATUS_IMPORTED, _("Imported")),
        (STATUS_INACTIVE, _("Inactive")),
        (STATUS_ACTIVE, _("Active")),
    )

    name = models.CharField(_('name'), max_length=190)
    name_ascii = models.CharField(_('ASCII name'), max_length=190, db_index=True)
    slug = models.SlugField(_('slug'), max_length=200, unique=True, blank=True)
    province = models.CharField(_('state/province'), max_length=3)
    country = models.CharField(_('country'), max_length=3)
    point = PointField(_('point'), null=True, blank=True)
    updated = models.DateTimeField(_("updated"))
    status = models.PositiveSmallIntegerField(_('status'), choices=STATUS_CHOICES, default=STATUS_NEW)

    objects = GeoManager()

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        abstract = True

    format_slug = "{name} {province} {country}"
    format_slug_counter = "{name} {province} {country} {counter}"

    @property
    def province_display(self):
        return self.province

    @property
    def country_display(self):
        return self.country

    def __str__(self):
        return "{0}, {1}, {2}".format(self.name, self.province_display, self.country)

    def save(self, *args, **kwargs):
        self.name_ascii = to_ascii(self.name)
        self.slug = city_slugify(self)
        self.updated = kwargs.pop('last_updated', timezone.now())

        # don't have a coordinate point? let's find one from our geocoder!
        if not self.point:
            try:
                data = geocode(country=self.country, city=self.name, region=self.province)
            except GeocodingError:
                # if we got in here, it's most likely because we're over the daily quota
                data = None

            if data and 'point' in data:
                point = data.get('point', {})
                self.point = Point(point.get('lng'), point.get('lat')) if 'lng' in point else None

        return super(BaseCity, self).save(*args, **kwargs)


class BasePostalCode(models.Model):
    city = models.ForeignKey(simple_geo_settings.SIMPLE_GEO_CITY_MODEL, verbose_name=_('city'), null=True, blank=True)
    code = models.CharField(_('zip/postal code'), max_length=16, db_index=True)
    point = PointField(_('point'), null=True, blank=True)
    updated = models.DateTimeField(_("updated"))

    objects = GeoManager()

    class Meta:
        verbose_name = _("Postal/Zip Code")
        verbose_name_plural = _("Postal/Zip Codes")
        abstract = True

    def __str__(self):
        return "{0}: {1}".format(self.code, self.city)

    def save(self, *args, **kwargs):
        self.updated = kwargs.pop('last_updated', timezone.now())
        return super(BasePostalCode, self).save(*args, **kwargs)


if simple_geo_settings.SIMPLE_GEO_CITY_MODEL == 'simple_geo.City':
    @python_2_unicode_compatible
    class City(BaseCity):
        pass


if simple_geo_settings.SIMPLE_GEO_POSTALCODE_MODEL == 'simple_geo.PostalCode':
    @python_2_unicode_compatible
    class PostalCode(BasePostalCode):
        pass
