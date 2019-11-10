#!/bin/sh -x

python tests.py
st=$?
cat logs/debug.log
exit $st
