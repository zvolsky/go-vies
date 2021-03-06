# -*- coding: utf-8 -*-

"""VIES (European VAT service) validation
Fork of (PyPI) django-vies (MIT licensed). Django dependencies were replaced.
  compared to django-vies: in single file, provides only the call of the service (returns validity and company info)
install_requires = ['suds-jurko >= 0.6', 'retrying >= 1.1.0']   # soap client, easy action retry

replaced django imports:
  from django.utils.functional import cached_property - has no dependency, so was pasted to here from django source
  from django.utils.translation import ugettext
                        - in VATIN._validate(), replaced with MSG_TRANSLATE - default 1:1, can be customized

TODO: It is good idea sometimes update VIES_OPTIONS from current version of django-vies/vies/__init__.py.

Usage:
  import go_vies
  go_vies.MSG_TRANSLATE = catalog.ugettext
                # optional, your translation function to translate english messages to current locale
                # this is really not important to set (used for 2 raised ValueError messages only)
  vatin = go_vies.VATIN('CZ', '26428091')
  vatin.is_valid()
    True
  vatin.result
    (reply){
       countryCode = "CZ"
       vatNumber = "26428091"
       requestDate = 2015-12-07
       valid = True
       name = "e-FRACTAL, s.r.o."
       address = "Vinohradská 1597/174
    PRAHA 3 - VINOHRADY
    130 00  PRAHA 3"
     }
  vatin.result['name']
    e-FRACTAL, s.r.o.
"""

from __future__ import (unicode_literals, absolute_import)

import logging
import re

from retrying import retry
from suds import WebFault
from suds.client import Client

logger = logging.getLogger('vies')

logging.basicConfig(level=logging.ERROR)
logging.getLogger('suds.client').setLevel(logging.INFO)

VIES_WSDL_URL = str('http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl')  # NOQA

# ------- added to go-vies to replace django imports of django-vies - BEGIN HERE -------
class cached_property(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        res = instance.__dict__[self.func.__name__] = self.func(instance)
        return res

def no_translate(msg):
    return msg

MSG_TRANSLATE = no_translate   # assign your translation function here, see Usage in module description above
# ------- added to go-vies to replace django imports of django-vies - END HERE -------

def dk_format(v):
    return '%s %s %s %s' % (v[:4], v[4:6], v[6:8], v[8:10])


def gb_format(v):
    if len(v) == 11:
        return '%s %s %s' % (v[:5], v[5:9], v[9:11])
    if len(v) == 14:
        return '%s %s' % (gb_format(v[:11]), v[11:14])
    return v


def fr_format(v):
    return '%s %s' % (v[:4], v[4:])


# TODO: update this (sometimes) from django-vies; Currently updated from: django-vies 2.2.2
VIES_OPTIONS = {
    'AT': ('Austria', re.compile(r'^ATU\d{8}$')),
    'BE': ('Belgium', re.compile(r'^BE0?\d{9}$')),
    'BG': ('Bulgaria', re.compile(r'^BG\d{9,10}$')),
    'HR': ('Croatia', re.compile(r'^HR\d{11}$')),
    'CY': ('Cyprus', re.compile(r'^CY\d{8}[A-Z]$')),
    'CZ': ('Czech Republic', re.compile(r'^CZ\d{8,10}$')),
    'DE': ('Germany', re.compile(r'^DE\d{9}$')),
    'DK': ('Denmark', re.compile(r'^DK\d{8}$'), dk_format),
    'EE': ('Estonia', re.compile(r'^EE\d{9}$')),
    'EL': ('Greece', re.compile(r'^EL\d{9}$')),
    'ES': ('Spain', re.compile(r'^ES[A-Z0-9]\d{7}[A-Z0-9]$')),
    'FI': ('Finland', re.compile(r'^FI\d{8}$')),
    'FR': ('France',
           re.compile(r'^FR[A-HJ-NP-Z0-9][A-HJ-NP-Z0-9]\d{9}$'),
           fr_format),
    'GB': ('United Kingdom',
           re.compile(r'^(GB(GD|HA)\d{3}|GB\d{9}|GB\d{12})$'),
           gb_format),
    'HU': ('Hungary', re.compile(r'^HU\d{8}$')),
    'IE': ('Ireland', re.compile(r'^IE\d[A-Z0-9\+\*]\d{5}[A-Z]{1,2}$')),
    'IT': ('Italy', re.compile(r'^IT\d{11}$')),
    'LT': ('Lithuania', re.compile(r'^LT(\d{9}|\d{12})$')),
    'LU': ('Luxembourg', re.compile(r'^LU\d{8}$')),
    'LV': ('Latvia', re.compile(r'^LV\d{11}$')),
    'MT': ('Malta', re.compile(r'^MT\d{8}$')),
    'NL': ('The Netherlands', re.compile(r'^NL\d{9}B\d{2}$')),
    'PL': ('Poland', re.compile(r'^PL\d{10}$')),
    'PT': ('Portugal', re.compile(r'^PT\d{9}$')),
    'RO': ('Romania', re.compile(r'^RO\d{2,10}$')),
    'SE': ('Sweden', re.compile(r'^SE\d{10}01$')),
    'SI': ('Slovenia', re.compile(r'^SI\d{8}$')),
    'SK': ('Slovakia', re.compile(r'^SK\d{10}$')),
}

VIES_COUNTRY_CHOICES = sorted(
    (('', '--'),) +
    tuple(
        (key, key)
        for key, value in VIES_OPTIONS.items())
)

MEMBER_COUNTRY_CODES = VIES_OPTIONS.keys()


class VATIN(object):
    """Object wrapper for the european VAT Identification Number."""

    _country_code = None

    @property
    def country_code(self):
        return self._country_code[:2].upper()

    _number = None

    @property
    def number(self):
        return self._number.upper()

    def __init__(self, country_code, number):
        self._country_code = country_code
        self._number = number
        self._validate()

    def is_valid(self):
        return all([
            self._verify(),
            self._validate()
        ])

    def _validate(self):
        if not re.match(r'^[a-zA-Z]', self.country_code):
            msg = MSG_TRANSLATE('%s is not a valid ISO_3166-1 country code.') % self.country_code
            raise ValueError(msg)
        elif self.country_code not in MEMBER_COUNTRY_CODES:
            msg = MSG_TRANSLATE('%s is not a VIES member country.') % self.country_code
            raise ValueError(msg)

        country = dict(map(
            lambda x, y: (x, y), ('country', 'validator', 'formatter'),
            VIES_OPTIONS[self.country_code]
        ))
        return country['validator'].match(
            '%s%s' % (self.country_code, self.number)
        )

    @cached_property
    def client(self):
        return Client(VIES_WSDL_URL)

    @retry(stop_max_delay=10000)
    def _verify(self):
        try:
            self.result = self.client.service.checkVat(
                self.country_code,
                self.number
            )
            return self.result.valid
        except WebFault as e:
            logger.exception(e)
            raise 
