import sys
from pylibimport.get_versions import HttpListVersions


__all__ = ['HttpListVersions']


# ===== Make the module callable =====
# https://stackoverflow.com/a/48100440/1965288  # https://stackoverflow.com/questions/1060796/callable-modules
MY_MODULE = sys.modules[__name__]


class DownloadModule(MY_MODULE.__class__):
    def __call__(self, package, version=None, download_dir='.', index_url='https://pypi.org/simple/', extensions=None,
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
        return HttpListVersions.download(package, version=version, download_dir=download_dir,
                                         index_url=index_url, extensions=extensions,
                                         min_version=min_version, exclude=exclude,
                                         check_compatibility=check_compatibility, chunk_size=chunk_size, **kwargs)

# Override the module make it callable
try:
    MY_MODULE.__class__ = DownloadModule  # Override __class__ (Python 3.6+)
    MY_MODULE.__doc__ = DownloadModule.__call__.__doc__
except (TypeError, Exception):
    # < Python 3.6 Create the module and make the attributes accessible
    sys.modules[__name__] = MY_MODULE = DownloadModule(__name__)
    for ATTR in __all__:
        setattr(MY_MODULE, ATTR, vars()[ATTR])


if __name__ == '__main__':
    import argparse

    P = argparse.ArgumentParser(description='List the versions for the given package')

    P.add_argument('package', type=str, help="Name of the package to list the versions for.")
    P.add_argument('-v', '--version', default=None, type=str, help="Version number you want to download.")
    P.add_argument('-o', '--download_dir', default='.', type=str, help="Directory to save the file to.")
    P.add_argument('-i', '--index_url', type=str, default='https://pypi.org/simple/', help='Index url to search.')
    P.add_argument('-e', '--extensions', metavar='N', type=str, nargs='+',
                   help='Allowed extensions (".whl", ".tar.gz")')
    P.add_argument('--min_version', type=str, default=None, help='Minimum version number to allow')
    P.add_argument('--check', '--check_compatibility', type=bool, default=True,
                   help='Check compatibility for this version of python.')
    P.add_argument('--exclude', metavar='N', type=str, nargs='*', help='Exclude versions')
    ARGS = P.parse_args()

    FILENAME = HttpListVersions.download(ARGS.package, version=ARGS.version, download_dir=ARGS.download_dir,
                                         index_url=ARGS.index_url, extensions=ARGS.extensions,
                                         min_version=ARGS.min_version, exclude=ARGS.exclude,
                                         check_compatibility=ARGS.check)
    print(FILENAME, 'saved!')
