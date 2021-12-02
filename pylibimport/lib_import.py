import os
import sys
import copy
import glob
import contextlib
import tempfile
import shutil
import tarfile
import importlib
import platform
from collections import OrderedDict
from packaging.version import parse as parse_version

from .utils import make_import_name, get_name_version
from .get_versions import HttpListVersions, uri_exists
from .run_pip import default_wait_func, pip_main, pip_bin, pip_proc
from .install import InstallError, original_system, import_module, install_lib, \
    register_install_type, remove_install_type, get_install_func, is_python_package, is_zip


if getattr(sys, 'frozen', False):
    import site
    if not getattr(site, '__file__', None):
        site.__file__ = sys.executable
        if not getattr(site, 'USER_BASE', None):
            site.USER_BASE = sys.executable
    if not getattr(site, 'USER_SITE', None):
        site.USER_SITE = sys.executable
    if not getattr(sys, 'prefix', None):
        sys.prefix = sys.executable


__all__ = ['VersionImporter']


class VersionImporter(object):
    """Import modules that have the same name, but different versions."""

    RUNNING_PYTHON_VERSION = "{}.{}.{}-{}"\
        .format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro, platform.architecture()[0])

    pip = staticmethod(pip_main)
    wait_func = staticmethod(default_wait_func)
    get_name_version = staticmethod(get_name_version)
    make_import_name = staticmethod(make_import_name)
    original_system = staticmethod(original_system)
    register_install_type = staticmethod(register_install_type)
    remove_install_type = staticmethod(remove_install_type)

    def __init__(self, download_dir=None, install_dir=None, index_url='https://pypi.org/simple/', python_version=None,
                 install_dependencies=False, reset_modules=True, clean_modules=False, contained_modules=None, **kwargs):
        """Initialize the library

        Args:
            download_dir (str)[None]: Name of the import directory.
            install_dir (str)[None]: Name of the directory to install the packages to.
            index_url (str)['https://pypi.org/simple/']: Index url for downloading files.
            python_version (str)[None]: Python version indicator used for the installation path (import_path).
            install_dependencies (bool)[False]: If True .whl files will install dependencies into the install_dir.
            reset_modules (bool)[True]: Reset the state of sys.modules after importing. Dependencies will not be loaded into sys.modules.
            clean_modules (bool)[False]: If True reset sys.modules before importing the module.
            contained_modules (dict)[None]: If a dict is given save all imported modules to this dictionary.
            **kwargs (dict): Unused given named arguments.
        """
        if python_version is None:
            python_version = self.RUNNING_PYTHON_VERSION

        self.python_version = python_version
        self._download_dir = None
        self._install_dir = None
        self.index_url = index_url
        self.install_dependencies = install_dependencies
        self.reset_modules = reset_modules
        self.clean_modules = clean_modules
        self.contained_modules = contained_modules
        self.modules = {}

        if download_dir is not None:
            self.set_download_dir(download_dir)
        if install_dir is not None:
            self.init(install_dir)

    def get_download_dir(self):
        """Return the download directory."""
        return self._download_dir

    def set_download_dir(self, value):
        """Set the download directory.

        Args:
            value (str)[None]: Directory to download .whl packages to.
        """
        if value is not None:
            value = os.path.abspath(str(value))
        self._download_dir = value

    download_dir = property(get_download_dir, set_download_dir)

    def get_install_dir(self):
        """Return the installation directory."""
        return self._install_dir

    def set_install_dir(self, value):
        """Set the installation directory.

        See Also:
            VersionImporter.make_import_path

        Args:
            value (str/None): Directory to install packages to.
                This directory will also use the Python version, library name, and library version to install.
        """
        self.init(value)

    install_dir = property(get_install_dir, set_install_dir)

    def init(self, install_dir=None):
        """Initialize this importer.

        Args:
            install_dir (str): Target directory. If None and self.install_dir is None use a temporary directory.
        """
        if install_dir is None:
            install_dir = self._install_dir
        if install_dir is None:
            install_dir = os.path.join(tempfile.gettempdir(), 'pylibimport')
        elif os.path.isfile(install_dir):
            install_dir = os.path.dirname(install_dir)

        # Remove the old directory
        self.remove_path(self._install_dir)

        # Setup this temp directory
        self._install_dir = os.path.abspath(str(install_dir))
        if not os.path.exists(self._install_dir):
            os.makedirs(self._install_dir)
        # sys.path.insert(0, self._install_dir)
        return self

    def make_import_path(self, libname='', libversion='', install_dir=None, python_version=None):
        """Return the import path that uses the install directory.

        Args:
            libname (str)['']: name of the package you want to import
            libversion (str)['']: Version number (1.2.3) for the package that you want to import
            install_dir (str)[None]: Installation directory.
            python_version (str)[None]: Python version to check installs for.
                This is found with sys.version info and platform.architecture.
                "{}.{}.{}-{}".format(version_info.major, version_info.minor, version_info.micro, architecture()[0])
                3.6.8-64bit
        """
        if install_dir is None:
            install_dir = self.install_dir
        if python_version is None:
            python_version = self.python_version
        return os.path.abspath(os.path.join(install_dir, python_version, libname, libversion))

    @staticmethod
    def remove_path(path, delete_path=False):
        """Remove the given path and sub paths. This also deletes the given path directory!"""
        # Remove the old directory
        if path is not None:
            for i in reversed(range(len(sys.path))):
                try:
                    if path in sys.path[i]:
                        sys.path.pop(i)
                except:
                    pass

            if delete_path:
                try:
                    shutil.rmtree(path, ignore_errors=True, onerror=None)
                except:
                    pass

    def add_path(self, path):
        """Add a path to sys.path and this.path."""
        if path not in sys.path:
            # self.paths.append(path)
            sys.path.insert(0, path)

    @staticmethod
    def rename_module(from_, to):
        """Rename a module/package and all submodules/subpackages to a new name.

        The main downside of this approach is that dependencies are not renamed. So there could be a dependency
        conflict when importing packages with the same name. It may be better to just reset sys.modules after import.

        Args:
            from_ (str): Name of the package that has already been imported.
            to (str): New name for the package.
        """
        length = len(from_)

        for k in list(sys.modules):
            if k.startswith(from_):
                sys.modules[to + k[length:]] = sys.modules[k]
                del sys.modules[k]

    def add_module(self, import_name, module):
        """Add a module to the system modules."""
        sys.modules[import_name] = module

    def iter_installed_versions(self, package=None, install_dir=None, python_version=None):
        """Iterate through installed versions of a packge yielding the available options.

        Args:
            package (str)[None]: Name of the package/library you want to ge the versions for (Example: "requests").
            install_dir (str)[None]: Installation directory.
            python_version (str)[None]: Python version to check installs for.
                This is found with sys.version info and platform.architecture.
                "{}.{}.{}-{}".format(version_info.major, version_info.minor, version_info.micro, architecture()[0])
                3.6.8-64bit

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): filename}
        """
        install_dir = install_dir or self.install_dir
        python_version = python_version or self.python_version
        imp_path = self.make_import_path('', '', install_dir=install_dir, python_version=python_version)

        exceptions = (AttributeError, ValueError, TypeError, FileNotFoundError, Exception)
        with contextlib.suppress(*exceptions):
            for name in os.listdir(imp_path):
                package_path = os.path.join(imp_path, name)
                if (package is None or package == name) and os.path.isdir(package_path):
                    for version in os.listdir(package_path):
                        with contextlib.suppress(*exceptions):
                            # Check if the installed directory has contents and yield the package info
                            path = os.path.abspath(os.path.join(package_path, version))
                            if len(os.listdir(path)) > 0:
                                import_name = self.make_import_name(name, version)
                                yield name, version, import_name, path

    def get_installed_versions(self, package=None, install_dir=None, python_version=None):
        """Return a series of package versions that have been installed for this python version.

        Args:
            package (str)[None]: Name of the package/library you want to ge the versions for (Example: "requests").
            install_dir (str)[None]: Installation directory.
            python_version (str)[None]: Python version to check installs for.
                This is found with sys.version info and platform.architecture.
                "{}.{}.{}-{}".format(version_info.major, version_info.minor, version_info.micro, architecture()[0])
                3.6.8-64bit

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): filepath}
        """
        it = self.iter_installed_versions(package, install_dir, python_version)
        return OrderedDict([((n, v), p) for (n, v, i, p) in it])

    def iter_downloaded_versions(self, package=None, download_dir=None):
        """Iterate through installed versions of a packge yielding the available options.

        Args:
            package (str)[None]: Name of the package/library you want to ge the versions for (Example: "requests").
            download_dir (str)[None]: Download directory.

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): filename}
        """
        download_dir = download_dir or self.download_dir

        exceptions = (AttributeError, ValueError, TypeError, FileNotFoundError, Exception)
        with contextlib.suppress(*exceptions):
            for filename in os.listdir(download_dir):
                with contextlib.suppress(*exceptions):
                    path = os.path.join(download_dir, filename)
                    if get_install_func(path) is not None:
                        name, version = self.get_name_version(path)
                        import_name = self.make_import_name(name, version)
                        if package is None or package == name or import_name == package or filename.endswith(package):
                            yield name, version, import_name, path

    def get_downloaded_versions(self, package=None, download_dir=None):
        """Return a series of package versions that have already been downloaded.

        Args:
            package (str)[None]: Name of the package/library you want to ge the versions for (Example: "requests").
            download_dir (str)[None]: Download directory.

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): filename}
        """
        it = self.iter_downloaded_versions(package, download_dir)
        return OrderedDict([((n, v), p) for (n, v, i, p) in it])

    def available_modules(self, use_downloads=True, directory=None):
        """Return a list of modules and their versions

        Args:
            use_downloads (bool)[True]: If True get the available versions from downloads.
                If False use the installed versions.
            directory (str)[None]: Directory to check. If None the default directories will be used.

        Returns:
            modules (list): List of [tuple(name, version, import_name, filepath)]
        """
        if use_downloads:
            versions = self.iter_downloaded_versions(download_dir=directory)
        else:
            versions = self.iter_installed_versions(install_dir=directory)

        return list(versions)

    def find_module(self, module_name, version=None, use_downloads=True):
        """Return the import dir module path for the given module name, import_name, or path.

        Args:
            module_name (str)[None]: Name of the package or module ("module" or "module.py")
            version (str)[None]: If given find a specific version.
            use_downloads (bool)[True]: If True use the download_dir. If False use the install_dir.
        """
        if use_downloads:
            versions = self.iter_downloaded_versions(module_name)
        else:
            versions = self.iter_installed_versions(module_name)

        results = (None, None, None, None)
        for (n, v, import_name, path) in versions:
            if import_name == module_name or path.endswith(module_name) or (n == module_name and v == version):
                return n, v, import_name, path
            elif n == module_name and (results[1] is None or parse_version(v) > parse_version(results[1])):
                # Make results this item but keep looking for newer versions.
                results = (n, v, import_name, path)

        # Check if requested version was found
        if version is not None and results[1] != version:
            if use_downloads:
                return self.find_module(module_name, version, use_downloads=False)
            return None, None, None, None  # Cannot find the correct version!
        else:
            return results

    def delete(self, project, version=None):
        """Delete all of the downloaded and installed files for the given project and version.

        Args:
            project (str): Project name.
            version (str)[None]: Project version to delete.
        """
        self.delete_downloaded(project, version)
        self.delete_installed(project, version)

    def delete_downloaded(self, name, version=None, download_dir=None):
        """Delete all of the downloaded files for the given project and version.

        Args:
            name (str/module): Package name.
            version (str)[None]: Project version to delete.
            download_dir (str)['.']: Download directory.
        """
        if not isinstance(name, str):
            try:
                name = name.__module__
            except (AttributeError, Exception):
                name = str(name)

        # Delete all of the downloaded files
        for filename in self.get_downloaded_versions(name, download_dir=download_dir).values():
            try:
                if version is None or self.get_name_version(filename)[1] == version:
                    os.remove(filename)
            except (OSError, Exception):
                pass

    def delete_installed(self, name, version=None):
        """Delete all of the installed files for the given project and version.

        Args:
            name (str/module): Package name.
            version (str)[None]: Project version to delete.
        """
        if not isinstance(name, str):
            with contextlib.suppress(AttributeError, Exception):
                if version is None:
                    version = name.__import_version__
            try:
                name = name.__module__
            except (AttributeError, Exception):
                try:
                    name = name.__name__
                except (AttributeError, Exception):
                    name = str(name)

        # Get the installed directory
        imp_path = self.make_import_path(name, version or '')
        if version is None:
            imp_path = os.path.dirname(imp_path)

        # Remove from sys.modules
        try:
            del sys.modules[__import_name__]
        except (AttributeError, KeyError, Exception):
            pass

        # Remove the library from the installed modules (This object and sys)
        try:
            if version is not None:
                versions = [version]
            else:
                versions = list(self.modules[name].keys())

            # Remove versions and modules
            for ver in versions:
                with contextlib.suppress(KeyError, AttributeError, Exception):
                    module = self.modules[name].pop(ver, None)
                with contextlib.suppress(KeyError, AttributeError, NameError, Exception):
                    del sys.modules[module.__name__]
                with contextlib.suppress(KeyError, AttributeError, NameError, Exception):
                    del sys.modules[module.__package__]
                with contextlib.suppress(KeyError, AttributeError, NameError, Exception):
                    del sys.modules[module.__import_name__]
                with contextlib.suppress(KeyError, AttributeError, NameError, Exception):
                    del module
        except (KeyError, ValueError, TypeError, Exception):
            pass

        # Always delete installed
        try:
            shutil.rmtree(imp_path, ignore_errors=True)
        except (OSError, Exception):
            # This may not be successful with C extensions.
            # When process is closed and new process tries to delete it should be successful.
            pass

    delete_module = delete_installed

    def uri_exists(self, index_url=None, timeout=None, **kwargs):
        """Return if the given URL/URI exists."""
        return uri_exists(index_url or self.index_url, timeout=timeout, **kwargs)

    def install_downloaded(self, package, version=None):
        """Install a downloaded package.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            version (str)[None]: Version number to find and download.
        """
        try:
            main_module = self.import_module(package, version)
            if main_module is None:
                self.delete_installed(package, version)
                return False
            return True
        except (ImportError, Exception):
            self.delete_installed(package, version)
            return False

    def download(self, package, version=None, download_dir=None, index_url=None, extensions='.whl',
                 min_version=None, exclude=None):
        """Download a package version to the download directory and return the file path that was saved.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            version (str)[None]: Version number to find and download.
            download_dir (str)['.']: Download directory.
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            extensions (list/str) [None]: List of allowed extensions (Example: [".whl", ".tar.gz"]).
            min_version (str)[None]: Minimum version to allow.
            exclude (list)[None]: List of versions that are excluded.

        Returns:
            filename (str)[None]: Filename of the downloaded package.
        """
        try:
            index_url = index_url or self.index_url
            download_dir = download_dir or self.download_dir
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            return HttpListVersions.download(package, version=version, download_dir=download_dir, index_url=index_url,
                                             extensions=extensions, min_version=min_version, exclude=exclude)
        except Exception as err:
            self.error(err)
            return None

    def get_versions(self, package, index_url=None, min_version=None, exclude=None):
        """Return a series of package versions.

        Args:
            package (str): Name of the package/library you want to ge the versions for (Example: "requests").
            index_url (str) ['https://pypi.org/simple/']: Simple url to get the package and it's versions from.
            min_version (str)[None]: Minimum version to allow.
            exclude (list)[None]: List of versions that are excluded.

        Returns:
            data (OrderedDict): Dictionary of {(package name, version): href}
        """
        try:
            index_url = index_url or self.index_url
            return HttpListVersions.get_versions(package, index_url=index_url, min_version=min_version, exclude=exclude)
        except Exception as err:
            self.error(err)
            return {}

    def error(self, error):
        """Handle an import error."""
        raise error

    def install(self, path, name=None, version=None, import_chain=None, extra_install_args=None):
        """Install the package with the name and version.

        Args:
            path (str): Path to install
            name (str)[None]: Name of the package/module.
            version (str)[None]: Version of the package/module.

        Returns:
            module (ModuleType)[None]: Module that was imported by the name or import_chain.
        """
        # Get a valid name and version
        if name is None or version is None:
            n, v = self.get_name_version(path)
            if name is None:
                name = n
            if version is None:
                version = v

        # Get the import path (install destination)
        imp_path = self.make_import_path(name, version)

        # Try to install the package
        install_kwargs = {
            'pip': self.pip,
            'wait_func': self.wait_func,
            'reset_modules': self.reset_modules,
            'install_dependencies': self.install_dependencies,
            'extra_install_args': extra_install_args,
            }
        install_lib(path, imp_path, **install_kwargs)

        # Try to import the installed module
        return self.import_path(imp_path, name, version, import_chain)

    def import_module(self, name, version=None, import_chain=None):
        """Import the given module or package."""
        # Check if valid path
        orig_name = name
        orig_version = version
        name, version, import_name, path = self.find_module(orig_name, version=version)
        if path is None:
            # Check if given was full path
            version = orig_version
            if os.path.exists(orig_name):
                path = orig_name
                name, v = self.get_name_version(path)
                if version is None:
                    version = v
            else:
                # Invalid path/name given!
                self.error(ModuleNotFoundError(orig_name))
                return

        # Set version
        if not version:
            version = '0.0.0'

        # Check if install_dir
        if self.install_dir is None:
            self.init()

        # Check if import name is available
        imp_path = self.make_import_path(name, version)
        module = self.import_path(imp_path, name, version, import_chain)
        if module is not None:
            return module

        # Try to install and import
        try:
            return self.install(path, name, version, import_chain)
        except Exception as err:
            self.error(err)

    def import_path(self, imp_path, name=None, version=None, import_chain=None,
                    reset_modules=None, clean_modules=None, contained_modules=None):
        """Import the given path.

        Args:
            imp_path (str): Path to import (path to file/folder).
            name (str)[None]: Name of the package to import.
            version (str)[None]: Version of the package to import. This makes the import name "name_version" if you
                want to use the normal python import after this.
            import_chain (str)[None]: Import chain ("custom.run_custom" to just import the function).
            reset_modules (bool)[None]: If True reset sys.modules back to the original sys.modules.
            clean_modules (bool)[None]: If True reset sys.modules before the context block is run.
            contained_modules (dict)[None]: If given and reset_modules save all imported modules to this dictionary.

        Returns:
            module (types.ModuleType/function/object): Object that was imported.
        """
        if reset_modules is None:
            reset_modules = self.reset_modules
        if clean_modules is None:
            clean_modules = self.clean_modules
        if contained_modules is None:
            contained_modules = self.contained_modules

        # Get name and version
        if name is None or version is None:
            n, v = self.get_name_version(imp_path)
            if name is None:
                name = n
            if version is None:
                version = v

        # Check if import_chain exists
        if import_chain is None:
            import_chain = name
        if import_chain in self.modules:
            modules = self.modules[import_chain]
            if version in modules:
                return modules[version]

        # Import the path
        try:
            module = import_module(imp_path, import_chain, reset_modules=reset_modules, clean_modules=clean_modules,
                                   contained_modules=contained_modules)
        except (ImportError, Exception) as err:
            module = None
            self.error(err)

        if module is not None:
            try:
                # Save in sys.modules with version
                import_name = self.make_import_name(import_chain, version)
                try:
                    module.__import_name__ = import_name
                except (AttributeError, Exception):
                    pass
                if not self.reset_modules:
                    self.rename_module(name, import_name)
                else:
                    self.add_module(import_name, module)

                # Save module to my modules
                try:
                    self.modules[import_chain][version] = module
                except (KeyError, Exception):
                    self.modules[import_chain] = {}
                    self.modules[import_chain][version] = module

                # Save the import version
                try:
                    module.__import_version__ = version
                except (AttributeError, Exception):
                    pass
            except (ValueError, TypeError, ImportError, Exception) as err:
                self.error(err)
        return module

    def cleanup(self):
        """Properly close the tempfile directory."""
        try:
            self.remove_path(self.install_dir, delete_path=True)
        except:
            pass
        return self

    close = cleanup


# ===== Make the module callable =====
# https://stackoverflow.com/a/48100440/1965288  # https://stackoverflow.com/questions/1060796/callable-modules
MY_MODULE = sys.modules[__name__]


class LibImportModule(MY_MODULE.__class__):

    MAIN_VERSION_IMPORTER = None

    def __call__(self, imp_path, name=None, version=None, import_chain=None,
                 reset_modules=None, clean_modules=None, contained_modules=None):
        """Import the given path.

        Args:
            imp_path (str): Path to import (path to file/folder).
            name (str)[None]: Name of the package to import.
            version (str)[None]: Version of the package to import. This makes the import name "name_version" if you
                want to use the normal python import after this.
            import_chain (str)[None]: Import chain ("custom.run_custom" to just import the function).
            reset_modules (bool)[None]: If True reset sys.modules back to the original sys.modules.
            clean_modules (bool)[None]: If True reset sys.modules before the context block is run.
            contained_modules (dict)[None]: If given and reset_modules save all imported modules to this dictionary.

        Returns:
            module (types.ModuleType/function/object): Object that was imported.
        """
        importer = self.MAIN_VERSION_IMPORTER
        if importer is None:
            importer  = self.MAIN_VERSION_IMPORTER = VersionImporter()
        return importer.import_path(imp_path, name=name, version=version, import_chain=import_chain,
                                    reset_modules=reset_modules, clean_modules=clean_modules,
                                    contained_modules=contained_modules)

# Override the module make it callable
try:
    MY_MODULE.__class__ = LibImportModule  # Override __class__ (Python 3.6+)
    MY_MODULE.__doc__ = LibImportModule.__call__.__doc__
except (TypeError, Exception):
    # < Python 3.6 Create the module and make the attributes accessible
    sys.modules[__name__] = MY_MODULE = LibImportModule(__name__)
    for ATTR in __all__:
        setattr(MY_MODULE, ATTR, vars()[ATTR])
