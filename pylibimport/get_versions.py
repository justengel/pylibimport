import os
import requests
import contextlib
from collections import OrderedDict
from urllib.parse import urljoin
from urllib.request import urlopen
from html.parser import HTMLParser
from packaging.version import parse as parse_version

from pylibimport.utils import get_name_version, EXTENSIONS, get_compatibility_tags, is_compatible


__all__ = ['uri_exists', 'HttpListVersions']


def uri_exists(uri):
    """Return if the given URI exists."""
    try:  # Faster check if url exists
        status_code = urlopen(uri).getcode()
        if 400 <= status_code < 500:
            raise ValueError('{} Client Error: Invalid url: {}'.format(status_code, uri))
        elif 500 <= status_code <= 600:
            raise ValueError('{} Server Error: Invalid url: {}'.format(status_code, uri))
        return True
    except (TypeError, ValueError, Exception):
        return False
    # try:
    #     with requests.get(str(uri), stream=True) as response:
    #         try:
    #             response.raise_for_status()
    #             return True
    #         except requests.exceptions.HTTPError:
    #             return False
    # except requests.exceptions.ConnectionError:
    #     return False


class HttpListVersions(HTMLParser):
    """Simple HTML parser to get the plugin, url names.

    Args:
        index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
        extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
        min_version (str)[None]: Minimum version to allow.
        exclude (list)[None]: List of versions that are excluded.
    """

    EXTENSIONS = EXTENSIONS
    is_compatible = staticmethod(is_compatible)

    def __init__(self, index_url='https://pypi.org/simple/', extensions=None, min_version=None, exclude=None,
                 check_compatibility=True, **kwargs):
        """Simple HTML parser to get the plugin, url names.

        Args:
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
            min_version (str)[None]: Minimum version to allow.
            exclude (list)[None]: List of versions that are excluded.
            check_compatibility (bool)[True]: Check if the whl file works for this version of Python.
        """
        if extensions is None:
            extensions = self.EXTENSIONS
        elif not isinstance(extensions, (list, tuple)):
            extensions = [extensions]

        if index_url and not index_url.endswith('/'):
            index_url += '/'

        if exclude is None:
            exclude = []
        elif not isinstance(exclude, (list, tuple)):
            exclude = [exclude]
        exclude = list(exclude)

        self.index_url = index_url
        self.extensions = extensions
        self.check_compatibility = check_compatibility
        self._min_version = min_version
        self._min_version_parsed = parse_version(min_version or '-999.-999.-999')
        self._exclude = exclude
        self.saved_data = OrderedDict()
        super().__init__(**kwargs)

    @property
    def min_version(self):
        return self._min_version

    @min_version.setter
    def min_version(self, value):
        self._min_version = value
        if self._min_version is None:
            self._min_version_parsed = parse_version('-999.-999.-999')
        else:
            self._min_version_parsed = parse_version(self._min_version)

    @property
    def exclude(self):
        return self._exclude

    @exclude.setter
    def exclude(self, value):
        if value is None:
            value = []
        elif not isinstance(value, (list, tuple)):
            value = [value]
        value = list(value)
        self._exclude = value

    def uri_exists(self, index_url=None):
        """Return if the given URL/URI exists."""
        return uri_exists(index_url or self.index_url)

    def handle_starttag(self, tag, attrs):
        href = ''

        with contextlib.suppress(ValueError, TypeError, Exception):
            attrs = dict(attrs)
            href = attrs.get('href', '')

        if tag == 'a' and (len(self.extensions) == 0 or any(ext in href for ext in self.extensions)):
            if not self.check_compatibility or self.is_compatible(href):
                href = urljoin(self.index_url, href)
                name, version = get_name_version(href)
                if (version not in self.exclude and parse_version(version) >= self._min_version_parsed and
                        (name, version) not in self.saved_data):
                    self.saved_data[(name, version)] = href
                # print(name, version, href)

    def is_my_version(self, href):
        attrs = get_py_version(href)

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        pass

    @classmethod
    def href_as_filename(cls, href):
        """Return the href as a filename."""
        filename = href.rsplit('/')[-1]
        if "#" in filename:
            filename = filename.split('#')[0]
        return filename

    @classmethod
    def get_versions(cls, package, index_url='https://pypi.org/simple/', extensions=None,
                     min_version=None, exclude=None, check_compatibility=True, **kwargs):
        """Return a series of package versions.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
            min_version (str)[None]: Minimum version to allow.
            exclude (list)[None]: List of versions that are excluded.
            check_compatibility (bool)[True]: Check if the whl file works for this version of Python.

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): href}
        """
        parser = cls(index_url, extensions, min_version=min_version, exclude=exclude,
                     check_compatibility=check_compatibility, **kwargs)
        resp = requests.get(parser.index_url + package)
        if resp.status_code != 200:
            raise ValueError('Invalid URL.')

        parser.feed(resp.text)
        return parser.saved_data

    @classmethod
    def download(cls, package, version=None, download_dir='.', index_url='https://pypi.org/simple/', extensions=None,
                 min_version=None, exclude=None, check_compatibility=True, chunk_size=1024, **kwargs):
        """Return a series of package versions.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            version (str)[None]: Version number to find and download.
            download_dir (str)['.']: Download directory.
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
            min_version (str)[None]: Minimum version to allow.
            exclude (list)[None]: List of versions that are excluded.
            check_compatibility (bool)[True]: Check if the whl file works for this version of Python.
            chunk_size (int)[1024]: Save the file with this chunk size.

        Returns:
            filename (str): Filename of the downloaded file.
        """
        versions = cls.get_versions(package, index_url=index_url, extensions=extensions, min_version=min_version,
                                    exclude=exclude, check_compatibility=check_compatibility, **kwargs)
        if version is None:
            href = versions[list(versions)[-1]]  # Get latest version
        else:
            href = versions.get((package, version), None)
        if href is None:
            raise ValueError('Invalid version given. Version not found!')

        filename = cls.href_as_filename(href)
        filename = os.path.abspath(os.path.join(download_dir, filename))

        r = requests.get(href)

        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)

        return filename


if __name__ == '__main__':
    import argparse

    P = argparse.ArgumentParser(description='List the versions for the given package')

    P.add_argument('package', type=str, help="Name of the package to list the versions for.")
    P.add_argument('-i', '--index_url', type=str, default='https://pypi.org/simple/', help='Index url to search.')
    P.add_argument('-e', '--extensions', metavar='N', type=str, nargs='+',
                   help='Allowed extensions (".whl", ".tar.gz")')
    P.add_argument('--min_version', type=str, default=None, help='Minimum version number to allow')
    P.add_argument('--check', type=bool, default=True, help='Check compatibility for this version of python.')
    P.add_argument('--exclude', metavar='N', type=str, nargs='*', help='Exclude versions')
    ARGS = P.parse_args()

    VERSIONS = HttpListVersions.get_versions(ARGS.package, index_url=ARGS.index_url, extensions=ARGS.extensions,
                                             min_version=ARGS.min_version, exclude=ARGS.exclude,
                                             check_compatibility=ARGS.check)
    for (N, V), HREF in VERSIONS.items():
        print(N, V, HREF)
