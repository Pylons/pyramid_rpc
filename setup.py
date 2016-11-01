##############################################################################
#
# Copyright (c) 2008-2010 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

import os
import sys

from setuptools import setup, find_packages

py_version = sys.version_info[:2]
PY3 = py_version[0] == 3

here = os.path.abspath(os.path.dirname(__file__))

try:
    README = open(os.path.join(here, 'README.rst')).read()
except:
    README = ''

install_requires = [
    'venusian>=1.0a7',
    'pyramid>=1.4',
]

tests_require = install_requires + [
    'WebTest',
]

testing_extras = tests_require + [
    'coverage',
    'nose',
]

docs_require = [
    'pylons-sphinx-themes',
    'Sphinx >= 1.3.1',
]

setup(name='pyramid_rpc',
      version='0.8',
      description='RPC support for the Pyramid web framework',
      long_description=README,
      classifiers=[
          "Intended Audience :: Developers",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Framework :: Pyramid",
      ],
      keywords='web wsgi pyramid pylons xml-rpc json-rpc amf',
      author="Ben Bangert",
      author_email="ben@groovie.org",
      maintainer='Michael Merickel',
      maintainer_email='michael@merickel.org',
      url='http://docs.pylonsproject.org/projects/pyramid_rpc/en/latest/',
      license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      tests_require=tests_require,
      install_requires=install_requires,
      extras_require={
          'testing': testing_extras,
          'docs': docs_require,
          'amf': ['pyamf'],
      },
      test_suite="pyramid_rpc.tests",
      )
