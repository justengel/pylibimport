import sys
import inspect
import light_process as lp

try:
    from pip._internal import main as PIP_MAIN
except (ImportError, AttributeError, Exception):
    try:
        from pip import main as PIP_MAIN
    except (ImportError, AttributeError, Exception):
        PIP_MAIN = None  # Not available for some reason.

from .utils import default_wait_func


__all__ = ['is_pip_main_available', 'pip_main', 'is_pip_proc_available', 'pip_proc']


def is_pip_main_available():
    """Return if the main pip function is available. Call get_pip_main before calling this function."""
    return PIP_MAIN is not None


is_pip_proc_available = is_pip_main_available


def pip_main(*args, **kwargs):
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
    if not is_pip_main_available():
        raise EnvironmentError('The main pip function is not available for this environment! Try pip_bin.')
    return PIP_MAIN(list(args))


def pip_proc(*args, wait_func=None, **kwargs):
    """Run a pip command using multiprocessing.

    https://pip.pypa.io/en/stable/reference/

    Note:
        pip_main may spawn another process. This may make executables not work.

    Example:

        >>> pip_proc('install', '-e', '../mylib')

    Args:
        *args (tuple/str): Arguments that are normally passed into pip.
        wait_func (callable/function): Call this function while waiting for pip to finish.
        **kwargs (dict/object)[None]: Catch extra arguments

    Raises:
        EnvironmentError: If pip could not be imported

    Returns:
        exitcode (int): Process exit code
    """
    if not is_pip_proc_available():
        raise EnvironmentError('The main pip function is not available for this environment! Try pip_bin.')

    if wait_func is None:
        wait_func = default_wait_func

    try:
        # Calling pip_main is bad practice (could do undesirable things). Run it in another process ...
        proc = lp.LightProcess(target=PIP_MAIN, args=(list(args), ))  # , name='pip_main')
        proc.start()
        while proc.exitcode is None:
            wait_func()
        proc.join(1)

        return getattr(proc, 'exitcode', 1)
    except (ValueError, TypeError, OSError, Exception) as err:
        return 1
