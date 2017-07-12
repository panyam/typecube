#!/bin/sh

rm -Rf build dist typecube.egg-info
python setup.py sdist
python setup.py bdist_wheel --universal
rm -Rf typecube.egg-info
