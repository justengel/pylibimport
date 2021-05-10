from .__meta__ import version as __version__

from .utils import make_import_name, get_name_version, \
    normalize_name, is_compatible, get_compatibility_tags, \
    parse, parse_filename, parse_wheel_filename, parse_sdist_filename, parse_meta, parse_setup

from .run_pip import default_wait_func, \
    find_file, IterProcess, pip_bin, \
    PIP_MAIN_FUNC, is_pip_main_available, pip_main, \
    is_pip_proc_available, pip_proc, pip_proc_flag

from .get_versions import uri_exists, HttpListVersions

from . import download

from .install import InstallError, original_system, import_module, install_lib, \
    register_install_type, remove_install_type, get_install_func, \
    is_python_package, py_install, is_zip, zip_install, whl_install

from .lib_import import VersionImporter


__all__ = [
    # meta
    '__version__'
    
    # utils
    'make_import_name', 'get_name_version', 'get_compatibility_tags',
    'parse_filename', 'parse_wheel_filename', 'parse_sdist_filename',
    'is_compatible', 'get_meta', 'get_setup_dict',

    # pip utils
    'default_wait_func',
    'find_file', 'IterProcess', 'pip_bin',
    'PIP_MAIN_FUNC', 'is_pip_main_available', 'pip_main',
    'is_pip_proc_available', 'pip_proc',

    # get versions
    'get_versions',   # Callable module
    'uri_exists', 'HttpListVersions',

    # download
    'download',  # Callable module

    # install
    'install',  # Callable module
    'InstallError', 'original_system', 'import_module', 'install_lib',
    'register_install_type', 'remove_install_type', 'get_install_func',
    'is_python_package', 'py_install', 'is_zip', 'zip_install', 'whl_install',

    # lib_import
    'lib_import',  # Callable module
    'VersionImporter',
    ]
