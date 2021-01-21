import sys
try:
    from . import fix_pip_subprocess
except (ImportError, Exception):
    pass


from .utils import default_wait_func
from .binary import find_file, IterProcess, pip_bin
from .main_func import PIP_MAIN_FUNC, is_pip_main_available, pip_main, is_pip_proc_available, pip_proc, pip_proc_flag


__all__ = ['default_wait_func', 'find_file', 'IterProcess', 'pip_bin',
           'PIP_MAIN_FUNC', 'is_pip_main_available', 'pip_main', 'is_pip_proc_available', 'pip_proc', 'pip_proc_flag']


# ===== Make the module callable =====
# https://stackoverflow.com/a/48100440/1965288  # https://stackoverflow.com/questions/1060796/callable-modules
MY_MODULE = sys.modules[__name__]


class RunPipModule(MY_MODULE.__class__):

    RUN_PIP = staticmethod(pip_main)

    def __call__(self, *args, **kwargs):
        """Run a pip command using the pip main function.

        https://pip.pypa.io/en/stable/reference/

        Note:
            pip_main may spawn another process. This may make executables not work.

        Example:

            >>> pip_main('install', '-e', '../mylib')

        Args:
            *args (tuple/str): Arguments that are normally passed into pip.
            **kwargs (dict/object)[None]: Catch extra arguments

        Raises:
            EnvironmentError: If pip could not be imported

        Returns:
            exitcode (int): Process exit code
        """
        return self.RUN_PIP(*args, **kwargs)


# Override the module make it callable
try:
    MY_MODULE.__class__ = RunPipModule  # Override __class__ (Python 3.6+)
    MY_MODULE.__doc__ = RunPipModule.__call__.__doc__
except (TypeError, Exception):
    # < Python 3.6 Create the module and make the attributes accessible
    sys.modules[__name__] = MY_MODULE = RunPipModule(__name__)
    for ATTR in __all__:
        setattr(MY_MODULE, ATTR, vars()[ATTR])
