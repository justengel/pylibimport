import os
import sys
import distutils.spawn
import subprocess
import threading

from .utils import default_wait_func


__all__ = ['find_file', 'IterProcess', 'pip_bin']


def find_file(*filenames, default=None):
    """Find a file using the python paths.

    Args:
        *filenames (tuple/str): File names to look for.
        default (str)[None]: If not found return this result.

    Returns:
        filename (str)[None]: Filename that was found or default argument.
    """
    # Check normal path
    for fname in filenames:
        try:
            # Should work on windows and linux to find executable/binaries like pip.exe
            exe = distutils.spawn.find_executable(fname)
            if exe is not None:
                return exe
        except (ValueError, TypeError, Exception):
            pass
        try:
            if os.path.exists(fname):
                return fname
        except (ValueError, TypeError, Exception):
            pass

    for path in sys.path:
        for fname in filenames:
            try:
                file = os.path.join(path, fname)
                if os.path.exists(file):
                    return file
            except (ValueError, TypeError, Exception):
                pass

    return default


class IterProcess(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._buffer = []
        self._toggle = 'out'
        self.stopped_out = False
        self.stopped_err = False
        try:
            self.iter_out = iter(self.stdout.readline)  # Iterator that yields data or ''
        except (AttributeError, Exception):
            self.iter_out = None
        try:
            self.iter_err = iter(self.stderr.readline)  # Iterator that yields data or ''
        except (AttributeError, Exception):
            self.iter_err = None

        self.th_out = threading.Thread(target=self.thread_read_buffer, args=(self.stdout,), daemon=True)
        self.th_err = threading.Thread(target=self.thread_read_buffer, args=(self.stderr,), daemon=True)
        self.th_out.start()
        self.th_err.start()

    def is_running(self):
        """Return if the process is still running."""
        return self.poll() is None

    def get_sys_file(self, file):
        """Return sys.stdout or sys.stderr based on the given file object buffer."""
        if file == self.stdout:
            return sys.stdout
        else:
            return sys.stderr

    def thread_read_buffer(self, file):
        """Read the buffer in a separate thread.

        Buffer reading is blocking, so this must be done in a separate thread.
        """
        while self.is_running():
            try:
                line = file.readline()
                if isinstance(line, bytes):
                    line = line.decode('utf-8', 'replace')
                self._buffer.append((line, file))
            except:
                pass

        # Try for longer?
        for _ in range(100):
            try:
                line = file.readline()
                if isinstance(line, bytes):
                    line = line.decode('utf-8', 'replace')
                self._buffer.append((line, file))
            except (ValueError, TypeError, Exception):
                break  # On error stop

    def next(self):
        try:
            line, file = self._buffer.pop(0)
        except (IndexError, ValueError, TypeError, Exception) as err:
            line, file = '', None

        if not line and not self.is_running():
            raise StopIteration
        return line, file

    def close(self):
        try:
            self.stdout.close()
        except (AttributeError, Exception):
            pass
        try:
            self.stderr.close()
        except (AttributeError, Exception):
            pass
        try:
            self.th_out.join()
        except (AttributeError, Exception):
            pass
        try:
            self.th_err.join()
        except (AttributeError, Exception):
            pass

    def __next__(self):
        return self.next()

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return exc_tb is None


def pip_bin(*args, wait_func=None, **kwargs):
    """Run pip using the binary/executable.

    https://pip.pypa.io/en/stable/reference/

    Example:

        >>> pip_bin('install', '-e', '../mylib')

    Args:
        *args (tuple/str): Arguments that are normally passed into pip.
        wait_func (callable/function): Call this function while waiting for pip to finish.
        **kwargs (dict/object)[None]: Catch extra arguments

    Returns:
        exitcode (int): Process exit code
    """
    pip_main_func = find_file('pip.exe', 'pip3', 'pip', default=None)
    if pip_main_func is None:
        raise EnvironmentError('Cannot find the pip binary!')

    if wait_func is None:
        wait_func = default_wait_func

    try:
        args = [pip_main_func] + list(args)
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE

        with IterProcess(args, **kwargs) as proc:
            for line, file in proc:
                wait_func()
                if line:
                    print(line, end='', file=proc.get_sys_file(file))
            # print('finishing')

        return getattr(proc, 'returncode', 1)
    except (ValueError, TypeError, OSError, Exception) as err:
        return 1
