from __future__ import unicode_literals
from django.contrib import admin

from .utils import get_city_model, get_postalcode_model
from .settings import SIMPLE_GEO_CITY_MODEL, SIMPLE_GEO_POSTALCODE_MODEL, SIMPLE_GEO_HIDE_ADMIN


if not SIMPLE_GEO_HIDE_ADMIN:
    if SIMPLE_GEO_CITY_MODEL == 'simple_geo.City':
        class CityAdmin(admin.ModelAdmin):
            list_display = ('name', 'slug', 'province', 'country')
            search_fields = ordering = ('name', 'name_ascii', 'slug')
            list_filter = ('country', 'province')
        admin.site.register(get_city_model(), CityAdmin)


    if SIMPLE_GEO_POSTALCODE_MODEL == 'simple_geo.PostalCode':
        class PostalCodeAdmin(admin.ModelAdmin):
            list_display = ('code', 'city')
            search_fields = ordering = ('code', 'city__name', 'city__name_ascii')
            list_filter = ('city__country', 'city__province')
        admin.site.register(get_postalcode_model(), PostalCodeAdmin)
