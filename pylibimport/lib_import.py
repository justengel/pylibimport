import os
import sys
import contextlib
import copy
import tempfile
import shutil
import tarfile
import importlib
import platform
from packaging.version import parse as parse_version
import multiprocessing as mp  # Multiprocessing will work in PyInstaller executable

from .utils import make_import_name, get_name_version, is_python_package

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
try:
    from pip._internal import main as pip_main
except (ImportError, AttributeError, Exception):
    from pip import main as pip_main


__all__ = ['VersionImporter']


class VersionImporter(object):
    """Import modules that have the same name, but different versions."""

    PYTHON_VERSION = "{}.{}.{}-{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro,
                                          platform.architecture()[0])

    DEFAULT_PYTHON_EXTENSIONS = ['.py', '.pyc', '.pyd']

    def __init__(self, import_dir=None, target_dir=None, python_extensions=None,
                 install_dependencies=False, reset_modules=True, **kwargs):
        """Initialize the library

        Args:
            import_dir (str)[None]: Name of the import directory.
            target_dir (str)[None]: Name of the directory to install the packages to.
            python_extensions (list)[None]: Available python extensions to try to import normally.
            install_dependencies (bool)[False]: If True .whl files will install dependencies into the target_dir.
            reset_modules (bool)[True]: Reset the state of sys.modules after importing.
                Dependencies will not be loaded into sys.modules.
            **kwargs (dict): Unused given named arguments.
        """
        if python_extensions is None:
            python_extensions = self.DEFAULT_PYTHON_EXTENSIONS

        self.import_dir = import_dir
        self._target_dir = None
        self.python_extensions = python_extensions
        self.install_dependencies = install_dependencies
        self.reset_modules = reset_modules
        self.modules = {}

        if target_dir is not None:
            self.init(target_dir)

    @property
    def target_dir(self):
        """Return the name of the target save directory."""
        return self._target_dir

    @target_dir.setter
    def target_dir(self, target_dir):
        self.init(target_dir)

    def make_import_path(self, libname, libversion):
        return os.path.join(self.target_dir, self.PYTHON_VERSION, libname, libversion)

    def init(self, target_dir=None):
        """Initialize this importer.

        Args:
            target_dir (str): Target directory. If None and self.target_dir is None use a temporary directory.
        """
        if target_dir is None:
            target_dir = self._target_dir
        if target_dir is None:
            target_dir = os.path.join(tempfile.gettempdir(), 'pylibimport')
        elif os.path.isfile(target_dir):
            target_dir = os.path.dirname(target_dir)

        # Remove the old directory
        self.remove_path(self._target_dir)

        # Setup this temp directory
        self._target_dir = str(target_dir)
        if not os.path.exists(self._target_dir):
            os.makedirs(self._target_dir)
        # sys.path.insert(0, self._target_dir)
        return self

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

    @contextlib.contextmanager
    def original_system(self, new_path=None, reset_modules=True):
        """Context manager to reset sys.path and sys.modules to the previous state before the context operation.

        Args:
            new_path (str)[None]: Temporarily add a path to sys.path before the operation.
            reset_modules (bool)[True]: If True reset sys.modules back to the original sys.modules.
        """
        modules = sys.modules.copy()
        paths = copy.copy(sys.path)
        path_cache = sys.path_importer_cache.copy()

        # Temporarily add the new path
        if new_path and new_path not in sys.path:
            sys.path.insert(0, new_path)

        yield

        if reset_modules:
            # sys.modules = modules  # For some reason this causes conflicts with relative imports?
            sys.modules.clear()
            sys.modules.update(modules)
        sys.path = paths
        sys.path_importer_cache = path_cache

    def iter_available_modules(self):
        """Iterate through importable packages."""
        for item in os.listdir(self.import_dir):
            try:
                path = os.path.join(self.import_dir, item)
                ext = os.path.splitext(item)[-1].lower()
                if (ext in self.python_extensions or
                        (ext == '' and is_python_package(path)) or
                        (ext == '.zip' or tarfile.is_tarfile(path) or ext == '.whl')):

                    name, version = get_name_version(path)
                    import_name = make_import_name(name, version)
                    yield name, version, import_name, path

            except (AttributeError, ValueError, TypeError, Exception):
                pass

    def available_modules(self):
        """Return a list of importable packages."""
        return [import_name for n, v, import_name, path in self.iter_available_modules()]

    def find_module(self, module_name, version=None):
        """Return the import dir module path for the given module name, import_name, or path."""
        # Search by import name
        results = (None, None, None, None)
        for n, v, i, p in self.iter_available_modules():
            if i == module_name or p.endswith(module_name) or (n == module_name and v == version):
                return n, v, i, p
            elif n == module_name and (results[1] is None or parse_version(v) > parse_version(results[1])):
                # Make results this item but keep looking for newer versions.
                results = (n, v, i, p)

        # Check if requested version was found
        if version is not None and results[1] != version:
            return None, None, None, None  # Cannot find the correct version!
        else:
            return results

    def delete_module(self, name, version=None):
        """Delete the given module from the target_dir.

        Args:
            name (str/ModuleType): String module name or module import_name. This may also be the module object
                that was imported.
            version (str)[None]: Version numbers (Example: 1.0.4).
        """
        if not isinstance(name, str):
            # Get the proper name and version from the module
            module = name
            try:
                version = module.__import_version__
                name = module.__module__  # Name of the module
            except (AttributeError, Exception):
                try:
                    # Hack where we save the import version
                    version = module.__version__
                    name = module.__module__  # Name of the module
                except (AttributeError, Exception):
                    # Manually find the module name and version ...
                    name = None
                    for n, vs in self.modules.items():
                        for v, m in vs.items():
                            if m == module:
                                name = n
                                version = v
                                break
        else:
            # Get the proper name and version
            name, version, import_name, path = self.find_module(name, version)

        #  Check if the name was valid
        if name is None:
            return name, version

        try:
            del self.modules[name][version]
        except:
            pass
        try:
            import_path = self.make_import_path(name, version)
            shutil.rmtree(import_path)
        except:
            pass
        return name, version

    def error(self, path, err):
        """Handle an import error."""
        raise err

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
                name, v = get_name_version(path)
                if version is None:
                    version = v
            else:
                # Invalid path/name given!
                self.error(orig_name, ModuleNotFoundError(orig_name))
                return

        # Set version
        if not version:
            version = '0.0.0'

        # Check if target_dir
        if self.target_dir is None:
            self.init()

        # Check if import name is available
        module = self._import_module(name, version, path, import_chain)
        if module is not None:
            return module

        # Check extension
        ext = os.path.splitext(path)[-1].lower()
        if ext in self.python_extensions or (ext == '' and is_python_package(path)):
            return self.py_import(name, version, path, import_chain)
        elif ext == '.zip' or tarfile.is_tarfile(path):
            return self.zip_import(name, version, path, import_chain)
        elif ext == '.whl':
            return self.whl_install(name, version, path, import_chain)

    def _import_module(self, name, version, path, import_chain=None):
        """Import the given module name from the given import path."""
        if import_chain is None:
            import_chain = name
        if import_chain in self.modules:
            modules = self.modules[import_chain]
            if version in modules:
                return modules[version]

        # Check if import name is available
        import_path = self.make_import_path(name, version)
        if os.path.exists(import_path):
            try:
                # Import the module
                with self.original_system(import_path, reset_modules=self.reset_modules):
                    module = importlib.import_module(import_chain)  # module = __import__(name)

                # Save in sys.modules with version
                import_name = make_import_name(import_chain, version)
                if not self.reset_modules:
                    self.rename_module(name, import_name)
                else:
                    self.add_module(import_name, module)

                # Save module to my modules
                if import_chain not in self.modules:
                    self.modules[import_chain] = {}
                self.modules[import_chain][version] = module

                # Save the import version
                try:
                    module.__import_version__ = version
                except:
                    pass

                return module
            except (ImportError, Exception) as err:
                self.error(path, err)
                return

    def py_import(self, name, version, path, import_chain=None):
        """Return the normal python import."""
        # Get the import path
        import_path = self.make_import_path(name, version)

        # Make the path exist in the target dir
        if not os.path.exists(import_path):
            os.makedirs(import_path)
            try:
                # Create symlink
                os.symlink(path, import_path, target_is_directory=os.path.isdir(path))
            except OSError:
                if os.path.isdir(path):
                    shutil.copytree(path, import_path)
                else:
                    shutil.copy(path, import_path)

        return self._import_module(name, version, path, import_chain)

    def zip_import(self, name, version, path, import_chain=None):
        """Import whl or zip files."""
        # Get the import path
        import_path = self.make_import_path(name, version)

        # Extract to import location.
        if not os.path.exists(import_path):
            os.makedirs(import_path)

            # Extract to zip
            shutil.unpack_archive(path, import_path)
            if not any(p == name for p in os.listdir(import_path)):
                # Move items up one directory
                for p in os.listdir(import_path):
                    nested_path = os.path.join(import_path, p)
                    for np in os.listdir(nested_path):
                        shutil.move(os.path.join(nested_path, np), os.path.join(import_path, np))
                    # shutil.rmtree(nested_path)

        return self._import_module(name, version, path, import_chain)

    def whl_install(self, name, version, path, import_chain=None):
        """Import whl or zip files."""
        # Get the import path
        import_path = self.make_import_path(name, version)

        # Install the wheel file to the target directory
        try:
            os.makedirs(import_path, exist_ok=True)
        except:
            pass
        with self.original_system(import_path, reset_modules=self.reset_modules):
            try:
                args = ['install', '--target', import_path, path]
                if not self.install_dependencies:
                    args.insert(1, '--no-deps')

                # Calling pip_main is bad practice (could do undesirable things). Run it in another process ...
                proc = mp.Process(target=pip_main, args=(args,))  #, name='pip_install')
                proc.start()
                proc.join()
                if proc.exitcode != 0:
                    raise ImportError('Could not import {}'.format(name))
            except (ImportError, Exception) as err:
                try:
                    shutil.rmtree(import_path)
                except:
                    pass
                self.error(path, err)
                return

        return self._import_module(name, version, path, import_chain)

    def cleanup(self):
        """Properly close the tempfile directory."""
        try:
            self.remove_path(self.target_dir, delete_path=True)
        except:
            pass
        return self

    close = cleanup
