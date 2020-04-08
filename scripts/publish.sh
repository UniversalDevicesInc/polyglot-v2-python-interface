#!/bin/bash -x
#
# For test.pypi.orig pass: -r https://test.pypi.org/pypi --skip-existing
#

twine upload $* dist/*
