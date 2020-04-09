#!/bin/sh -x

python scripts/tests.py
st=$?
cat logs/debug.log
exit $st
