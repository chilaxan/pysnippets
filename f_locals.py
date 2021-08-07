from ctypes import *
from _ctypes import Py_INCREF, Py_DECREF
from collections.abc import MutableMapping
import sys

base_size = sizeof(c_void_p)
FrameType = type(sys._getframe())

@lambda c:c()
class Null:
    def __repr__(self):
        return '<NULL>'

class f_locals(MutableMapping):
    __invert__ = None
    def __init__(self, frame):
        self.frame = frame
        self._r = False

    def __repr__(self):
        if self._r:
            return '...'
        self._r = True
        try:
            return f'locals({dict(self.items())})'
        finally:
            self._r = False

    def _getlocp(self):
        addr = id(self.frame) + FrameType.__basicsize__ - base_size
        buffer = addr.to_bytes(base_size, sys.byteorder)
        return POINTER(py_object).from_buffer_copy(buffer)

    def __getitem__(self, key):
        names = list(self)
        if key not in names:
            raise KeyError(key)
        loc_p = self._getlocp()
        try:
            return loc_p[names.index(key)]
        except ValueError:
            return Null

    def __setitem__(self, key, value):
        names = list(self)
        if key not in names:
            raise KeyError(key)
        loc_p = self._getlocp()
        if value is not Null:
            Py_INCREF(value)
            loc_p[names.index(key)] = value
        else:
            del self[key]

    def __delitem__(self, key):
        names = list(self)
        if key not in names:
            raise KeyError(key)
        loc_p = self._getlocp()
        try:
            Py_DECREF(loc_p[names.index(key)])
        except ValueError:
            pass
        cast(loc_p, POINTER(c_void_p))[names.index(key)] = None

    def __iter__(self):
        return iter(self.frame.f_code.co_varnames)

    def __len__(self):
        return len(self.frame.f_code.co_varnames)

def getclsdict(cls):
    mapping = cls.__dict__
    if isinstance(mapping, dict):
        return mapping
    return py_object.from_address(id(mapping) + 2 * sizeof(c_void_p)).value

# Here we take adavantage of `tp_as_number.nb_invert` and the `FrameType.f_locals.__get__`
# having compatible C signatures
# These modifications cause the following execution flow when `frame.f_locals` occurs:
# (FrameType + offsetof(PyGetSetDef))[index of `f_locals`].get(frame)
# We have set `get` to `tp_as_number.nb_invert`, so this in turn looks up
# `__invert__` in the types dictionary mapping and calls that python function with the argument `frame`
# the result of this python function is returned by `get`

# get function address of nb_invert from `f_locals` class
# we dont need to care about the offset that `nb_invert` is at because it is the only non-null address
nb_invert = sum(POINTER(c_ssize_t*36).from_address(id(f_locals) + 12 * base_size).contents)
# delete the attribute, we already have the address we needed
del f_locals.__invert__
# offsetof(PyGetSetDef) // base_size == 31
# the `f_locals` PyGetSetDef happens to be first in this array
# NOTE: alternatively, this address could be retrieved from `FrameType.f_locals`
#       which is a `getset_descriptor` object
getset_ptr = c_void_p.from_address(id(FrameType) + 31 * base_size).value
# `get` is the second pointer in the PyGetSetDef structure
# NOTE: the first is a `c_char_p` that contains its attribute name
f_locals_get_ptr = c_void_p.from_address(getset_ptr + base_size)
# we set this function pointer to `nb_invert`
f_locals_get_ptr.value = nb_invert
# set `__invert__` in the class dictionary
# otherwise `nb_invert` will raise an AttributeError
getclsdict(FrameType)['__invert__'] = lambda frame: f_locals(frame)
# NOTE: This does not enable `~frame == frame.f_locals`
#       To do that, `FrameType.tp_as_number.nb_invert` must be set

__builtins__.locals = lambda:sys._getframe(1).f_locals

def test_reassign():
    abc = 'Old Value'
    print(abc) # 'Old Value'
    locals()['abc'] = 'New Value'
    print(abc) # 'New Value'

def test_preassign():
    locals()['abc'] = 'New Value'
    print(abc)
    abc = None # forces abc to be a local

def test_dellocal():
    abc = 'Old Value'
    del locals()['abc']
    print(abc)

def test_setnull():
    abc = 'Old Value'
    locals()['abc'] = Null
    print(abc)

def set_local(name, value):
    frame = sys._getframe(1)
    frame.f_locals[name] = value

def foo():
    set_local('abc', 'Value')
    print(abc)
    abc = None # forces abc to be a local
