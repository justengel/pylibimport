import os
import re
import sys

from packaging.tags import sys_tags, parse_tag
from packaging.utils import canonicalize_name, canonicalize_version
from packaging.version import Version, InvalidVersion

from package_parser import parse, \
    normalize_name, is_compatible, get_compatibility_tags, get_supported, SUPPORTED, \
    parse_wheel_filename, parse_sdist_filename, parse_custom, parse_meta, parse_setup, parse_module, \
    remove_possible_md5, try_attrs


__all__ = ['make_import_name', 'get_name_version',
           'is_compatible', 'get_compatibility_tags',
           'parse', 'parse_filename', 'parse_wheel_filename', 'parse_sdist_filename', 'parse_meta', 'parse_setup']


parse_filename = parse


def make_import_name(name, version=''):
    """Return an import name using the name and version."""
    if version:
        converted_version = normalize_name(str(version))
        if '.' in name:
            first, other = name.split('.', 1)
            return '{}_{}.{}'.format(first, converted_version, other)
        else:
            return '{}_{}'.format(name, converted_version)
    else:
        return name


def get_name_version(filename):
    """Parse a wheel filename.

    Args:
        filename (str): Wheel filename that ends in .whl or sdist filename that ends with .tar.gz.

    Returns:
        name (str): Name of the library
        version (str): Version of the library
    """
    attrs = parse(filename)
    name = normalize_name(str(attrs['name']))
    version = str(attrs['version']) or '0.0.0'
    return name, version


def get_compatibility_tags(filename):
    """Get the python version and os architecture to check against.

    Args:
        filename (str): Wheel filename that ends in .whl or sdist filename that ends with .tar.gz.

    Returns:
        pyver (str)['py3']: Python version of the library py3 or cp38 ...
        abi (str)['none']: ABI version abi3, none, cp33m ...
        plat (str)['any']: Platform of the library none, win32, or win_amd64
    """
    # Parse the wheel filename or sdist filename
    attrs = parse_filename(filename)

    # Assume correct version if not found.
    return (attrs.get('pyver', 'py{}'.format(sys.version_info[0])),
            attrs.get('abi', 'none'),
            attrs.get('plat', 'any'))
