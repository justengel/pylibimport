"""
Try to implement a finder and loader to have files natively install.
"""
import os
import sys
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec

from .lib_import import VersionImporter


__all__ = [
    'init_finder', 'init_loader', 'loader',
    'import_name_to_name_version', 'PyLibImportFinder', 'PyLibImportLoader',
    ]


LOADER = None
FINDER = None


def init_finder(**kwargs):
    """Create the global VersionImporter and initialize the finder."""
    global FINDER

    if len(kwargs) > 0:
        init_loader(**kwargs)

    # I must insert it at the beginning so it goes before FileFinder
    FINDER = PyLibImportFinder()
    sys.meta_path.insert(0, FINDER)


def init_loader(download_dir=None, install_dir=None, index_url='https://pypi.org/simple/', python_version=None,
                install_dependencies=False, reset_modules=True, clean_modules=False, contained_modules=None, **kwargs):
    """Create the general global importer."""
    global LOADER

    LOADER = PyLibImportLoader(download_dir=download_dir,
                               install_dir=install_dir,
                               index_url=index_url,
                               python_version=python_version,
                               install_dependencies=install_dependencies,
                               reset_modules=reset_modules,
                               clean_modules=clean_modules,
                               contained_modules=contained_modules, **kwargs)

    return LOADER


def loader():
    """Return the global VersionImporter/Loader."""
    global LOADER
    return LOADER


def import_name_to_name_version(import_name):
    """Convert the import name to a name and version.

    Args:
        import_name (str): Import name with a version (Ex: "custom_0_0_0")

    Returns:
        name (str): Just the package name (Ex: "custom")
        version (str)[None]: Version of the package (Ex: "0.0.0")
    """
    s = str(import_name).split('_')
    for i, n in enumerate(s):
        if len(n) > 0 and n.isdigit():
            return '_'.join(s[:i]), '.'.join(s[i:])

    return import_name, None


class PyLibImportFinder(MetaPathFinder):
    @classmethod
    def find_spec(cls, full_name, paths=None, target=None):
        imp = loader()
        name, version = import_name_to_name_version(full_name)
        if imp is None or version is None:
            return None

        # Check if name and version is available to the importer
        name, version, import_name, path = imp.find_module(name, version)
        if path is not None:
            import_path = imp.make_import_path(name, version)
            return ModuleSpec(import_name, imp, origin=import_path)


class PyLibImportLoader(VersionImporter, Loader):
    @classmethod
    def exec_module(cls, module):
        imp = module.__spec__.loader
        import_name = module.__spec__.name
        import_path = module.__spec__.origin
        name, version = import_name_to_name_version(import_name)
        try:
            imp.import_module(name, version)  # If success will be sys.modules["custom_0_0_0"]
            module.__path__ = [import_path]
        except (ImportError, Exception):
            pass
