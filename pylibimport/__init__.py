from .__meta__ import version as __version__

from .utils import make_import_name, get_name_version, get_compatibility_tags, is_compatible, is_python_package

from .pip_utils import default_wait_func, \
    find_file, IterProcess, pip_bin, \
    PIP_MAIN_FUNC, is_pip_main_available, pip_main, \
    is_pip_proc_available, pip_proc, pip_proc_flag

from .get_versions import uri_exists, HttpListVersions
from .lib_import import InstallError, VersionImporter
