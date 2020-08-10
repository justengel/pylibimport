import os
import requests
import contextlib
from collections import OrderedDict
from urllib.parse import urljoin
from html.parser import HTMLParser

from pylibimport.utils import get_name_version, EXTENSIONS


__all__ = ['HttpListVersions']


class HttpListVersions(HTMLParser):
    """Simple HTML parser to get the plugin, url names.

    Args:
        index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
        extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
    """

    EXTENSIONS = EXTENSIONS

    def __init__(self, index_url='https://pypi.org/simple/', extensions=None, **kwargs):
        """Simple HTML parser to get the plugin, url names.

        Args:
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
        """
        if extensions is None:
            extensions = self.EXTENSIONS
        elif not isinstance(extensions, (list, tuple)):
            extensions = [extensions]

        if index_url and not index_url.endswith('/'):
            index_url += '/'

        self.index_url = index_url
        self.extensions = extensions
        self.saved_data = OrderedDict()
        super().__init__(**kwargs)

    def handle_starttag(self, tag, attrs):
        href = ''

        with contextlib.suppress(ValueError, TypeError, Exception):
            attrs = dict(attrs)
            href = attrs.get('href', '')

        if tag == 'a' and (len(self.extensions) == 0 or any(ext in href for ext in self.extensions)):
            href = urljoin(self.index_url, href)
            name, version = get_name_version(href)
            if (name, version) not in self.saved_data:
                self.saved_data[(name, version)] = href
            # print(name, version, href)

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
    def get_versions(cls, package, index_url='https://pypi.org/simple/', extensions=None, **kwargs):
        """Return a series of package versions.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): href}
        """
        parser = cls(index_url, extensions, **kwargs)
        resp = requests.get(parser.index_url + package)
        if resp.status_code != 200:
            raise ValueError('Invalid URL.')

        parser.feed(resp.text)
        return parser.saved_data

    @classmethod
    def download(cls, package, version=None, download_dir='.',
                 index_url='https://pypi.org/simple/', extensions=None, chunk_size=1024, **kwargs):
        """Return a series of package versions.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            version (str)[None]: Version number to find and download.
            download_dir (str)['.']: Download directory.
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
            chunk_size (int)[1024]: Save the file with this chunk size.

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): href}
        """
        versions = cls.get_versions(package, index_url=index_url, extensions=extensions, **kwargs)
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
    ARGS = P.parse_args()

    VERSIONS = HttpListVersions.get_versions(ARGS.package, index_url=ARGS.index_url, extensions=ARGS.extensions)
    for (N, V), HREF in VERSIONS.items():
        print(N, V, HREF)
