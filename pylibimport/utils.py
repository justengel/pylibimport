import os
import re


__all__ = ['make_import_name', 'get_name_version', 'is_python_package']


WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<version>\d.*?))(-(?P<build>\d.*?))?
     -(?P<pyver>[a-z].+?)-(?P<abi>.+?)-(?P<plat>.+?)(\.whl|\.dist-info|\.zip|\.tar|\.tar\.gz)?$""",
    re.VERBOSE).match

NAME_VER_RE = re.compile(
        r"""^(?P<namever>(?P<name>.+?)-(?P<version>[.a-zA-Z0-9]*))""",
    re.VERBOSE).match

_CONVERT_UNDERSCORE = re.compile("[^\w]+")


def make_import_name(name, version=''):
    """Return an import name using the name and version."""
    if version:
        return '{}_{}'.format(name, _CONVERT_UNDERSCORE.sub('_', str(version)))
    else:
        return name


def get_name_version(filename):
    """Parse a wheel filename.

    Args:
        filename (str): Wheel filename that ends in .whl

    Returns:
        attrs (dict): Wheel filename parsed attributes
            * namever - Name with version (Ex. 'numpy-1.15.4+mkl')
            * name - Name of the library (Ex. 'numpy')
            * version - Version of the library (Ex. '1.15.4+mkl')
            * build - Build Version of the library. Must start with a digit (Ex. None)
            * pyver - Python Version for the library (Ex. 'cp38', 'py3')
            * abi - abi tag of the library (Ex. 'cp38m')
            * plat - OS platform of the library (Ex. 'win_amd64')
            * import_name - New import name with the version (Ex. 'numpy_1_14_4_mkl')
    """
    filename = os.path.basename(filename)
    try:
        attrs = WHEEL_INFO_RE(filename).groupdict()
    except:
        try:
            if filename.endswith('.tar.gz'):
                filename = os.path.splitext(filename)[0]
            attrs = NAME_VER_RE(os.path.splitext(filename)[0]).groupdict()
        except:
            attrs = {'name': os.path.splitext(filename)[0], 'version': ''}
            if '-' in attrs['name']:
                split = attrs['name'].split('-')
                attrs['name'] = split[0]
                attrs['version'] = split[1]

    if not attrs['version']:
        attrs['version'] = '0.0.0'
    return attrs['name'], attrs['version']


def is_python_package(directory):
    """Return if the given directory has an __init__.py."""
    return os.path.exists(os.path.join(directory, '__init__.py'))
