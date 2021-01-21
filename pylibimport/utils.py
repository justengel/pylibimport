import os
import re
import sys

from packaging.tags import sys_tags, parse_tag
from packaging.utils import canonicalize_name, canonicalize_version
from packaging.version import Version, InvalidVersion


__all__ = ['make_import_name', 'get_name_version', 'get_compatibility_tags',
           'parse_filename', 'parse_wheel_filename', 'parse_sdist_filename',
           'is_compatible', 'get_meta', 'get_setup_dict']


def get_supported():
    tags = [(t.interpreter, t.abi, t.platform) for t in sys_tags()]
    for t in list(tags):
        if t[1].startswith('cp'):
            tags.append((t[0], t[1]+'m', t[2]))  # Copy tags with 'm' added to the abi
    return tags


SUPPORTED = get_supported()
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
        filename (str): Wheel filename that ends in .whl or sdist filename that ends with .tar.gz.

    Returns:
        name (str): Name of the library
        version (str): Version of the library
    """
    if os.path.isdir(filename):
        filename = os.path.join(filename, 'setup.py')
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

    # Parse the wheel filename or sdist filename
    attrs = parse_filename(filename)
    return attrs['name'], str(attrs['version'])


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


def parse_filename(filename):
    """Parse a wheel filename or sdist filename and return the attributes.

    Args:
        filename (str): Wheel filename that ends in .whl or sdist filename that ends with .tar.gz.

    Returns:
        attrs (dict): Dictionary of attributes "name", "version", "build", "pyver", "abi", "plat".
    """
    attrs = {'name': '', 'version': '0.0.0', 'build': '', 'pyver': 'py{}'.format(sys.version_info[0]),
             'abi': 'none', 'plat': 'any'}

    # Format the filename
    filename = filename.split('#', 1)[0]  # Strip off md5 if applicable
    filename = os.path.basename(filename)

    try:
        # Use parse_wheel_filename
        values = parse_wheel_filename(filename)
        attrs['name'], attrs['version'], attrs['build'], attrs['pyver'], attrs['abi'], attrs['plat'] = values

    except (AttributeError, ValueError, Exception):
        try:
            # Use parse_sdist_filename
            values = parse_sdist_filename(filename)
            attrs['name'], attrs['version'] = values
        except (AttributeError, ValueError, Exception):
            fname = os.path.splitext(filename)[0]
            attrs['name'] = fname

            count = fname.count('-')
            if count >= 4:
                count = 4

            # Split the filename
            parts = fname.rsplit('-', count)

            # Find name and version
            if len(parts) >= 2:
                attrs['name'] = parts[0]
                attrs['version'] = parts[1]
            if '-' in attrs['name']:
                split = attrs['name'].split('-')
                attrs['name'] = split[0]
                attrs['version'] = split[1]

            # Find other
            py_ver_found = False
            for item in parts[2:]:  # Skip name and version
                if not py_ver_found and (item.startswith('py') or item.startswith('cp')):
                    py_ver_found = True
                    attrs['pyver'] = item
                elif (item.startswith('cp') or item.startswith('none') or item.startswith('abi')):
                    attrs['abi'] = item
                elif item.startswith('any') or item.startswith('win') or item.startswith('linux'):
                    attrs['plat'] = item

    return attrs


def parse_wheel_filename(filename):
    """Parse the wheel filename.

    Modified from: https://github.com/pypa/packaging/blob/master/packaging/utils.py
    """
    if not filename.endswith(".whl"):
        raise ValueError("Invalid wheel filename (extension must be '.whl'): {0}".format(filename))

    # Remove extension
    filename = filename[:-4]

    # Check number of dashes
    dashes = filename.count("-")
    if dashes < 4:  # Could always have more dashing in the "name" portion
        raise ValueError("Invalid wheel filename (wrong number of parts): {0}".format(filename))

    # Split the filename components
    name, version, pyver, abi, plat = filename.rsplit("-", 4)
    build = ''

    try:
        # Check if name contains versoin
        if '.' in name:
            raise ValueError  # name contains name and version while version is build?
        version = Version(version)
    except (InvalidVersion, ValueError, Exception):
        try:
            build = version
            name, version = name.rsplit('-', 1)
            version = Version(version)  # If this fails it is just invalid
        except (InvalidVersion, ValueError, Exception) as err:
            raise ValueError('Invalid version string "{}"!'.format(version)) from err

    # Check name formatting
    if "__" in name or re.match(r"^[\w\d._]*$", name, re.UNICODE) is None:
        raise ValueError("Invalid project name: {}".format(filename))

    name = canonicalize_name(name_part)
    return (name, version, build, pyver, abi, plat)


def parse_sdist_filename(filename):
    """Parse the sdist filename.

    Modified from: https://github.com/pypa/packaging/blob/master/packaging/utils.py
    """
    # Remove extension
    filename = os.path.splitext(filename)[0]  # '.tar.gz', '.zip', '.dist-info'
    if filename.endswith('.tar'):
        filename = os.path.splitext(filename)[0]

    # We are requiring a PEP 440 version, which cannot contain dashes,
    # so we split on the last dash.
    name, version = filename.rsplit('-', 1)
    name = canonicalize_name(name)
    version = Version(version)
    return (name, version)


def is_compatible(filename):
    """Return if the given filename is available on this system."""
    pyver, abi, plat = get_compatibility_tags(filename)
    return (pyver, abi, plat) in SUPPORTED


def get_meta(filename):
    """Return the metadata dictionary from the given filename."""
    with open(filename, 'r') as f:
        meta = {}
        exec(compile(f.read(), filename, 'exec'), meta)
        return meta


def get_setup_dict(filename):
    """Return the metadata dictionary from setup.py file."""
    meta = {}

    try:
        from setuptools import setup as orig_setup

        def my_setup(**attrs):
            meta.update(attrs)
        sys.modules['setuptools'].setup = my_setup

        cwd = os.getcwd()
        with open(filename, 'r') as f:
            os.chdir(os.path.abspath(os.path.dirname(filename)))
            exec(compile(f.read(), '<string>', 'exec'),
                 {'__name__': '__main__', '__file__': os.path.abspath(filename)})  # Hack __name__ and __file__ just in case
            os.chdir(cwd)

        sys.modules['setuptools'].setup = orig_setup

    except (ImportError, Exception):
        pass  # Failed to import

    return meta
