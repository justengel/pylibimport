import os
import sys
import copy
import shutil
import tarfile
import contextlib
import importlib
from collections import OrderedDict

from pylibimport.utils import get_name_version
from pylibimport.run_pip import default_wait_func, pip_main


__all__ = ['InstallError', 'original_system', 'import_module', 'install_lib',
           'register_install_type', 'remove_install_type', 'get_install_func',
           'is_python_package', 'py_install', 'is_zip', 'zip_install', 'whl_install']


class InstallError(Exception):
    pass


DEFAULT_MODULES = [  # sys.builtin_module_names  # (builtin_module_names doesn't work unfortunately)
    'sys', 'builtins', '_frozen_importlib', '_imp', '_warnings', '_frozen_importlib_external', '_io', 'marshal', 'nt',
    '_thread', '_weakref', 'winreg', 'time', 'zipimport', '_codecs', 'codecs', 'encodings.aliases', 'encodings',
    'encodings.utf_8', 'encodings.cp1252', '_signal', '__main__', 'encodings.latin_1', '_abc', 'abc', 'io', '_stat',
    'stat', '_collections_abc', 'genericpath', 'ntpath', 'os.path', 'os', '_sitebuiltins', '_locale', '_bootlocale',
    'site', 'atexit'
    ]


@contextlib.contextmanager
def original_system(new_path=None, reset_modules=True, clean_modules=False, **kwargs):
    """Context manager to reset sys.path and sys.modules to the previous state before the context operation.

    Args:
        new_path (str)[None]: Temporarily add a path to sys.path before the operation.
        reset_modules (bool)[True]: If True reset sys.modules back to the original sys.modules.
        clean_modules (bool)[False]: If True reset sys.modules before the context block is run.
    """
    modules = sys.modules.copy()
    paths = copy.copy(sys.path)
    path_cache = sys.path_importer_cache.copy()

    # Temporarily add the new path
    if new_path and new_path not in sys.path:
        sys.path.insert(0, new_path)

    if clean_modules:
        sys.modules.clear()
        # sys.path_importer_cache = {}  # Do I need this?
        for pkg in DEFAULT_MODULES:
            try:
                sys.modules[pkg] = modules[pkg]
            except (AttributeError, KeyError, Exception):
                pass

    yield

    if reset_modules:
        # sys.modules = modules  # For some reason this causes conflicts with relative imports?
        sys.modules.clear()
        sys.modules.update(modules)
    sys.path = paths
    sys.path_importer_cache = path_cache


def import_module(path, import_chain=None, reset_modules=True, clean_modules=False, contained_modules=None):
    """Import the given module name from the given import path.

    Args:
        path (str): Directory which contains the module to import.
        import_chain (str): Chain to import with.
        reset_modules (bool)[True]: If True reset sys.modules back to the original sys.modules.
        clean_modules (bool)[False]: If True reset sys.modules before importing the module.
        contained_modules (dict)[None]: If a dict is given save all imported modules to this dictionary.

    Returns:
        module (ModuleType): Module object that was imported.

    Raises:
        ImportError: If the import is unsuccessful.
    """
    if import_chain is None:
        import_chain, _ = get_name_version(path)
    if os.path.isfile(path):
        path = os.path.dirname(path)

    if os.path.exists(path):
        # Import the module
        with original_system(os.path.abspath(path), reset_modules=reset_modules, clean_modules=clean_modules):
            module = importlib.import_module(import_chain)  # module = __import__(name)
            if isinstance(contained_modules, dict):
                contained_modules.update(sys.modules)

        return module


INSTALL_TYPES = OrderedDict()


def register_install_type(type_func, install_func=None):
    """Register an install function.

    Args:
        type_func (str/callable/function): Extension string '.py' or callable function that takes in
            a path, **kwargs and returns a bool if the path is installable by this install function.
        install_func (callable/function)[None]: If None decorator. Function that takes in a path, dest and installs
            the path to the destination.

    Returns:
         install_func (callable/function): Decorator or install_func
    """
    if install_func is None:
        def decorator(install_func):
            return register_install_type(type_func, install_func)
        return decorator

    INSTALL_TYPES[type_func] = install_func
    return install_func


def remove_install_type(type_func):
    """Remove the registered type_func for installing."""
    try:
        INSTALL_TYPES.pop(type_func)
    except:
        pass
    try:
        INSTALL_TYPES.remove(type_func)
    except:
        pass


def get_install_func(path, **kwargs):
    """Find the installation function for the given path and keyword arguments.

    Args:
        path (str): Path to the installable file.
        **kwargs (dict): Dictionary of keyword arguments passed into the registered type_func to see if it can install
            the path.

    Returns:
        install_func (callable/function)[None]: Function to install the path with.
            Should take in (path, dest, **kwargs) and return True if installed or False if directory existed.
    """
    ext = os.path.splitext(path)[-1]
    install_func = INSTALL_TYPES.get(ext, None)
    if install_func is None:
        install_func = INSTALL_TYPES.get(ext.lower(), None)
        if install_func is None:
            for type_func, install_func in INSTALL_TYPES.items():
                try:
                    if callable(type_func) and type_func(path, **kwargs):
                        return install_func
                except (ValueError, TypeError, AttributeError, Exception):
                    pass

            return None  # No install func found!

    # Return the install func
    return install_func


def install_lib(path, dest, **kwargs):
    """Try to install the given path to the destination.

    Args:
        path (str): Path to the file or folder to install.
        dest (str): Destination path.

    Returns:
        installed (bool): If True it was installed this time. If False directory already existed.
    """
    install_func = get_install_func(path, **kwargs)
    if callable(install_func):
        return install_func(path, dest, **kwargs)

    raise InstallError('Invalid install type! Cannot install the given path "{}"!'.format(path))


def is_python_package(directory, **kwargs):
    """Return if the given directory has an __init__.py."""
    return os.path.exists(os.path.join(directory, '__init__.py'))


@register_install_type(is_python_package)
@register_install_type('.pyc')
@register_install_type('.pyd')
@register_install_type('.py')
def py_install(path, dest, *args, **kwargs):
    """Return the normal python import.

    Args:
        path (str): Path to the file or folder to install.
        dest (str): Destination path.

    Returns:
        installed (bool): If True it was installed this time. If False directory already existed.
    """
    # Make the path exist in the target dir
    try:
        os.makedirs(dest, exist_ok=True)
    except:
        pass

    try:
        try:
            # Create symlink
            os.symlink(path, dest, target_is_directory=os.path.isdir(path))
        except OSError:
            if os.path.isdir(path):
                shutil.copytree(path, dest)
            else:
                shutil.copy(path, dest)
    except (ValueError, TypeError, AttributeError, OSError, Exception) as err:
        raise InstallError('Failed to install "{}"'.format(path)) from err
    return True


def is_zip(path, **kwargs):
    return tarfile.is_tarfile(path)


@register_install_type(is_zip)
@register_install_type('.tar.gz')
@register_install_type('.zip')
def zip_install(path, dest, *args, **kwargs):
    """Install .zip or .tar.gz files.

    Args:
        path (str): Path to the file or folder to install.
        dest (str): Destination path.

    Returns:
        installed (bool): If True it was installed this time. If False directory already existed.

    Raises:
        InstallError: If any part of the installation fails.
    """
    # Extract to import location.
    try:
        os.makedirs(dest, exist_ok=True)
    except:
        pass

    # Extract to zip
    try:
        shutil.unpack_archive(path, dest)

        # Check if package name not in extracted directory and move up one directory
        name, _ = get_name_version(path)
        if not any(p == name for p in os.listdir(dest)):
            # Move items up one directory
            for p in os.listdir(dest):
                nested_path = os.path.join(dest, p)
                for np in os.listdir(nested_path):
                    shutil.move(os.path.join(nested_path, np), os.path.join(dest, np))
                shutil.rmtree(nested_path)
    except (ValueError, TypeError, AttributeError, OSError, Exception) as err:
        raise InstallError('Failed to install "{}"'.format(path)) from err
    return True


@register_install_type('.whl')
def whl_install(path, dest, *args, pip=None, extra_install_args=None, install_dependencies=False, wait_func=None,
                reset_modules=True, contained_modules=None, **kwargs):
    """Import whl or zip files and return the installed module.

    Args:
        dest (str): Destination path.
        path (str): Path to the zip file.
        pip (callable/function): pip function to install with (Takes in parameters passed into pip). Should be able
            to take in any keyword arguments and ignore them.
        extra_install_args (list/str): List of extra parameters to pass into the pip install command.
            Note: the '--target' argument is already being used.
        install_dependencies (bool)[False]: If True .whl files will install dependencies into the install_dir.
        wait_func (callable/function)[None]: Function called while waiting for pip to finish (passed into pip).
        reset_modules (bool)[True]: If True reset sys.modules back to the original sys.modules.
        contained_modules (dict)[None]: If given and reset_modules save all imported modules to this dictionary.

    Returns:
        installed (bool): If True it was installed this time. If False directory already existed.
    """
    if pip is None:
        pip = pip_main
    if not extra_install_args:
        extra_install_args = []
    elif isinstance(extra_install_args, str):
        extra_install_args = [extra_install_args]
    if wait_func is None:
        wait_func = default_wait_func

    # Install the wheel file to the target directory
    try:
        os.makedirs(dest, exist_ok=True)
    except:
        pass
    with original_system(dest, reset_modules=reset_modules, contained_modules=contained_modules):
        args = ['install', '--target', dest] + extra_install_args + [path]
        if not install_dependencies:
            args.insert(1, '--no-deps')

        exitcode = pip(*args, wait_func=wait_func)
        if exitcode != 0:
            try:
                shutil.rmtree(dest)
            except (OSError, Exception):
                pass
            raise InstallError('Could not install using pip with arguments {}'.format(args))
        return True
    return False


# ===== Make the module callable =====
# https://stackoverflow.com/a/48100440/1965288  # https://stackoverflow.com/questions/1060796/callable-modules
MY_MODULE = sys.modules[__name__]


class InstallModule(MY_MODULE.__class__):

    def __call__(self, path, dest, **kwargs):
        """Try to install the given path to the destination.

        Args:
            path (str): Path to the file or folder to install.
            dest (str): Destination path.

        Returns:
            installed (bool): If True it was installed this time. If False directory already existed.
        """
        return install_lib(path, dest, **kwargs)

# Override the module make it callable
try:
    MY_MODULE.__class__ = InstallModule  # Override __class__ (Python 3.6+)
    MY_MODULE.__doc__ = InstallModule.__call__.__doc__
except (TypeError, Exception):
    # < Python 3.6 Create the module and make the attributes accessible
    sys.modules[__name__] = MY_MODULE = InstallModule(__name__)
    for ATTR in __all__:
        setattr(MY_MODULE, ATTR, vars()[ATTR])


if __name__ == '__main__':
    import argparse

    P = argparse.ArgumentParser(description='Install the path to the destination')

    P.add_argument('path', type=str, help="Path to the python module, zip, whl, or folder to install.")
    P.add_argument('dest', type=str, help="Destination to install to.")


    # .whl arguments
    P.add_argument('--extra_install_args', type=str, default=None, help='Extra pip installation arguments.')
    P.add_argument('--install_dependencies', default=True, action='store_true',
                   help='If given install the dependencies in the destination as well.')

    ARGS = P.parse_args()
    KWARGS = {'extra_install_args': ARGS.extra_install_args, 'install_dependencies': ARGS.install_dependencies}
    if install_lib(ARGS.path, ARGS.dest, **KWARGS):
        print('Installed successfully!')
    else:
        print('Path already existed and may have already been installed.')
