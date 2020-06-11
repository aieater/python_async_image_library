#!/usr/bin/env python3
from __future__ import print_function
import importlib
import os


def to_bool(s):
    return s in [1, "True", "TRUE", "true", "1", "yes", "Yes", "Y", "y", "t", "on"]


DEBUG = False
if "DEBUG" in os.environ:
    DEBUG = to_bool(os.environ["DEBUG"])
    if DEBUG:
        try:
            import __builtin__
        except ImportError:
            import builtins as __builtin__
        import inspect

        def lpad(s, c):
            return s[0:c].ljust(c)

        def rpad(s, c):
            if len(s) > c:
                return s[len(s) - c:]
            else:
                return s.rjust(c)

        def print(*args, **kwargs):
            s = inspect.stack()
            __builtin__.print("\033[44m%s@%s(%s):\033[0m " % (rpad(s[1][1], 20), lpad(str(s[1][3]), 10), rpad(str(s[1][2]), 4)), end="")
            return __builtin__.print(*args, **kwargs)


def _pre_():
    print("\033[A                                                                \033[A", flush=True)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


_dopen = open
