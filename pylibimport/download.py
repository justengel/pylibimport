from pylibimport.get_versions import HttpListVersions


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
    P.add_argument('--exclude', metavar='N', type=str, nargs='*', help='Exclude versions')
    ARGS = P.parse_args()

    FILENAME = HttpListVersions.download(ARGS.package, version=ARGS.version, download_dir=ARGS.download_dir,
                                         index_url=ARGS.index_url, extensions=ARGS.extensions,
                                         min_version=ARGS.min_version, exclude=ARGS.exclude)
    print(FILENAME, 'saved!')
