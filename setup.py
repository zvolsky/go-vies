from distutils.core import setup
setup(
  name = 'go-vies',
  py_modules = ['go_vies'],
  version = '1.0.3',
  description = 'VIES VAT Validation (like django-vies without Django dependencies)',
  requires = ['retrying (>=1.3.3)', 'suds (>=0.4)'],
  author = 'Mirek Zvolsky',
  author_email = 'zvolsky@seznam.cz',
  url = 'https://github.com/zvolsky/go-vies',
  download_url = 'https://github.com/zvolsky/go-vies/tarball/1.0.3',
  keywords = ['vies', 'vat'],
  classifiers = [],
)
