#!/bin/sh

rm -Rf build dist typelib.egg-info
python setup.py sdist
python setup.py bdist_wheel --universal
rm -Rf typelib.egg-info
