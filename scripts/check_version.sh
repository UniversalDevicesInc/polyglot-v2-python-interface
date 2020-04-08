#!/bin/bash

module=polyinterface
idx=https://pypi.org/pypi
if [[ "$1" == "-t" ]]; then
  idx=https://test.pypi.org/pypi
fi
echo "Checking $module versions on $idx"

# Put in a tmp file for now, cause pip gives weird errors sometimes
#python3 -m pip search $module >.rver
rver=`head -1 <.rver | sed -E 's/.*\((.*)\).*/\1/'`

# Version on current directory
cver=`python setup.py --version`

echo "$module PyPi version=$rver"
echo "$module setup.py version=$cver"
if [[ "$rver" == "$cver" ]]; then
  echo "MATCHED"
  exit 0
else
  echo "NOTMATCHED"
  exit 1
fi
