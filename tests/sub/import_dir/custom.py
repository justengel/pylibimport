import functools


def run_hello(name=' world!'):
    return 'hello' + name


run_custom = functools.partial(run_hello, name='')
