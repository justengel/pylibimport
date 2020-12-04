import os
import re
import sys


__all__ = ['EXTENSIONS', 'make_import_name', 'get_name_version', 'is_python_package', 'get_setup_dict', 'get_meta']


EXTENSIONS = ['.whl', '.tar.gz', '.tar', '.zip', '.dist-info']

WHEEL_INFO_RE = re.compile(
        r"""^(?P<namever>(?P<name>.+?)-(?P<version>(\d*)(\.(a|b|rc)?\d+)?(\.(post|dev)?\d+)?))(-(?P<build>\d.*?))?
         -(?P<pyver>[a-z].+?)-(?P<abi>.+?)-(?P<plat>.+?)(\.whl|\.dist-info|\.zip|\.tar\.gz|\.tar)?$""",
        re.VERBOSE).match

NAME_VER_RE = re.compile(
        r"""^(?P<namever>(?P<name>.+?)-(?P<version>[.a-zA-Z0-9]*))""",
    re.VERBOSE).match

_CONVERT_UNDERSCORE = re.compile("[^\w]+")


def make_import_name(name, version=''):
    """Return an import name using the name and version."""
    if version:
        converted_version = _CONVERT_UNDERSCORE.sub('_', str(version))
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
        filename (str): Wheel filename that ends in .whl

    Returns:
        name (str): Name of the library
        version (str): Version of the library
    """
    if filename.lower().endswith('setup.py'):
        filename = os.path.abspath(str(filename))
        try:
            meta = get_setup_dict(filename)
            return meta['name'], meta['version']
        except (ImportError, PermissionError, FileNotFoundError, KeyError, Exception):
            pass

        # Try finding the __meta__.py file to read. This is the only way I can read the proper name and version.
        filename = os.path.dirname(filename)
        for fname in os.listdir(filename):
            try:
                meta = get_meta(os.path.join(filename, fname, '__meta__.py'))
                return meta['name'], meta['version']
            except (FileNotFoundError, PermissionError, TypeError, KeyError, Exception):
                pass

    # Try parsing the wheel file format
    filename = os.path.basename(filename)
    try:
        attrs = WHEEL_INFO_RE(filename).groupdict()
    except:
        try:
            if '.tar.gz' in filename:  # .tar.gz has two "." so the extension needs to be removed twice.
                filename = os.path.splitext(filename)[0]
            attrs = NAME_VER_RE(os.path.splitext(filename)[0]).groupdict()
        except:
            attrs = {'name': os.path.splitext(filename)[0], 'version': '0.0.0'}
            if '-' in attrs['name']:
                split = attrs['name'].split('-')
                attrs['name'] = split[0]
                attrs['version'] = split[1]

    # Get a version
    version = attrs.get('version', '0.0.0')

    return attrs['name'], version


def is_python_package(directory):
    """Return if the given directory has an __init__.py."""
    return os.path.exists(os.path.join(directory, '__init__.py'))


def get_meta(filename):
    """Return the metadata dictionary from the given filename."""
    with open(filename, 'r') as f:
        meta = {}
        exec(compile(f.read(), filename, 'exec'), meta)
        return meta


def get_setup_dict(filename):
    """Return the metadata dictionary from setup.py file."""
    from setuptools import setup

    meta = {}
    def my_setup(**attrs):
        meta.update(attrs)
    sys.modules['setuptools'].setup = my_setup

    cwd = os.getcwd()
    with open(filename, 'r') as f:
        os.chdir(os.path.abspath(os.path.dirname(filename)))
        exec(compile(f.read(), '<string>', 'exec'),
             {'__name__': '__main__', '__file__': os.path.abspath(filename)})  # Hack __name__ and __file__ just in case
        os.chdir(cwd)

    sys.modules['setuptools'].setup = setup
    return meta

