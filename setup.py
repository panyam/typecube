#!/usr/bin/env python
import os
import re
import ast
import sys
from distutils.sysconfig import get_python_lib

from setuptools import find_packages
from setuptools import setup

# Warn if we are installing over top of an existing installation. 
overlay_warning = False
if "install" in sys.argv:
    lib_paths = [get_python_lib()]
    if lib_paths[0].startswith("/usr/lib/"):
        # We have to try also with an explicit prefix of /usr/local in order to
        # catch Debian's custom user site-packages directory.
        lib_paths.append(get_python_lib(prefix="/usr/local"))
    for lib_path in lib_paths:
        existing_path = os.path.abspath(os.path.join(lib_path, "typecube"))
        if os.path.exists(existing_path):
            # We note the need for the warning here, but present it after the
            # command is run, so it's more likely to be seen.
            overlay_warning = True
            break


# Any packages inside the typecube source folder we dont want in the packages
EXCLUDE_FROM_PACKAGES = [ ]

def get_version():
    with open('typecube/__init__.py', 'rb') as f:
        _version_re = re.compile(r'__version__\s+=\s+(.*)')
        return str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

def get_description():
    return open("README.rst").read()

setup(name='typecube',
      version=get_version(),
      author='Sriram Panyam',
      author_email='sri.panyam@gmail.com',
      requires = ["enum34", "ipdb", "wheel", "PyYaml" ],
      extras_require={'docs': ['Sphinx>=1.1']},
      keywords=['languages', 'type system', 'types'],
      url='https://github.com/panyam/typecube',
      long_description=get_description(),
    description=("Utilities and library to model types and type systems"),
    zip_safe = False,
    license='BSD',
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    scripts=['bin/clean_install.sh', 'bin/package.sh'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Compilers',
    ],
)


if overlay_warning:
    sys.stderr.write("""

========
WARNING!
========

You have just installed typecube over top of an existing
installation, without removing it first. Because of this,
your install may now include extraneous files from a
previous version that have since been removed from
typecube . This is known to cause a variety of problems. You
should manually remove the

%(existing_path)s

directory and re-install typecube.

""" % {"existing_path": existing_path})
