import sys
import inspect
import multiprocessing as mp
import light_process as lp

from pylibimport.run_pip.utils import default_wait_func


try:
    from pip._internal.cli.main import main as PIP_MAIN_FUNC
except (ImportError, AttributeError, Exception):
    try:
        from pip._internal import main as PIP_MAIN_FUNC
    except (ImportError, AttributeError, Exception):
        try:
            from pip import main as PIP_MAIN_FUNC
        except (ImportError, AttributeError, Exception):
            PIP_MAIN_FUNC = None  # Not available for some reason.


__all__ = ['PIP_MAIN_FUNC', 'is_pip_main_available', 'pip_main', 'is_pip_proc_available', 'pip_proc', 'pip_proc_flag']


def is_pip_main_available():
    """Return if the main pip function is available. Call get_pip_main before calling this function."""
    return PIP_MAIN_FUNC is not None


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
    return PIP_MAIN_FUNC(list(args))


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
        proc = lp.LightProcess(target=PIP_MAIN_FUNC, args=(list(args), ))  # , name='pip_main')
        proc.start()
        while proc.exitcode is None:
            wait_func()
        proc.join(1)

        return getattr(proc, 'exitcode', 1)
    except (ValueError, TypeError, OSError, Exception) as err:
        return 1


def _pip_proc_flag(*args, finished_flag=None, success_flag=None, **kwargs):
    """Run pip and flag when it is finished."""
    ret = 1
    try:
        ret = PIP_MAIN_FUNC(list(args))
    finally:
        if ret == 0 and success_flag is not None:
            success_flag.set()
        if finished_flag is not None:
            finished_flag.set()
    return ret


def pip_proc_flag(*args, wait_func=None, **kwargs):
    """Old multiprocessing does not successfully use exitcode to check if the process is finished."""
    if wait_func is None:
        wait_func = default_wait_func

    try:
        kwargs['finished_flag'] = finished_flag = mp.Event()
        kwargs['success_flag'] = success_flag = mp.Event()
        proc = mp.Process(target=_pip_proc_flag, args=args, kwargs=kwargs)
        proc.start()
        while not finished_flag.is_set():
            wait_func()
        proc.join(1)
        try:
            proc.terminate()  # Make sure it closed
        except:
            pass

        exitcode = getattr(proc, 'exitcode', 1)
        if success_flag.is_set():
            exitcode = 0
        return exitcode
    except(ValueError, TypeError, Exception):
        return 1
