import time


__all__ = ['default_wait_func']


def default_wait_func():
    time.sleep(0.1)
