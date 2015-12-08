# go-vies
## Python library for VIES (European VAT validation service)

- based on django-vies module but without Djan(go-) dependency
- compared to django-vies: in single file, provides only the call of the service (returns validity and company info)

- still requires these modules installed: retrying (easy action retry), suds (soap client)
- django imports were replaced:
  -- from django.utils.functional import cached_property - has no dependency, so was pasted to here from django source
  -- from django.utils.translation import ugettext
                        in VATIN._validate(), replaced with 1:1 "translation" MSG_TRANSLATE - can be customized

It is good idea to update VIES_OPTIONS from current version of django-vies/vies/__init__.py.

Usage:
```
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
```
