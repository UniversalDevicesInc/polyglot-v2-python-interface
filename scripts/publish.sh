#!/bin/bash -x
#
# For test.pypi.orig pass: --index https://test.pypi.org/pypi --skip-existing
#

twine upload dist/* $*
