import ctypes
from ctypes.util import find_library
import os

from evemu import const
from evemu import exception


class EvEmuBase(object):
    """
    A base wrapper class for the evemu functions, accessed via ctypes.
    """
    def __init__(self, library=""):
        if not library:
            library = const.LIB
        self._lib = ctypes.CDLL(library, use_errno=True)
        self._libc = ctypes.CDLL(find_library("c"), use_errno=True)

    def _call0(self, api_call, *parameters):
        result = api_call(*parameters)
        if result == 0 and self.get_c_errno() != 0:
            raise exception.ExecutionError, "%s: %s" % (
                api_call.__name__, self.get_c_error())
        return result

    def _call(self, api_call, *parameters):
        result = api_call(*parameters)
        if result < 0 and self.get_c_errno() != 0:
            raise exception.ExecutionError, "%s: %s" % (
                api_call.__name__, self.get_c_error())
        return result

    def get_c_errno(self):
        return ctypes.get_errno()

    def get_c_error(self):
        return os.strerror(ctypes.get_errno())

    def get_c_lib(self):
        return self._libc

    def get_lib(self):
        return self._lib
