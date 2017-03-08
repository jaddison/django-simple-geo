from __future__ import unicode_literals
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='django-simple-geo',
    description='Simple Django city, state, country geo-spatially aware model and utilities.',
    long_description='View `django-simple-geo documentation on Github  <https://github.com/jaddison/django-simple-geo>`_.',
    author='James Addison',
    author_email='addi00+github.com@gmail.com',
    packages=[
        'simple_geo',
        'simple_geo.management',
        'simple_geo.management.commands',
    ],
    version='0.2.0',
    url='http://github.com/jaddison/django-simple-geo',
    keywords=['django', 'geo', 'gis', 'geodjango', 'geocoding', 'longitude', 'latitude', 'geospatial', 'cities', 'coordinates'],
    license='BSD',
    classifiers=[
      'Development Status :: 4 - Beta',
      'License :: OSI Approved :: BSD License',
      'Intended Audience :: Developers',
      'Environment :: Web Environment',
      'Programming Language :: Python',
      'Framework :: Django',
      'Topic :: Internet :: WWW/HTTP :: WSGI',
    ],
)
