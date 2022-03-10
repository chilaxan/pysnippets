from ctypes import (
    sizeof, c_void_p,
    py_object, c_ssize_t,
    pointer, POINTER,
    addressof
)
from _ctypes import Py_INCREF, Py_DECREF
from collections.abc import MutableMapping
import sys

base_size = sizeof(c_void_p)
FrameType = type(sys._getframe())

Null = type('',(),{'__repr__':lambda s:'<NULL>'})()

def cast(cobj, ctyp):
    # custom `cast` function (with no safety checks)
    return ctyp.from_address(addressof(cobj))

class f_locals(MutableMapping):
    __invert__ = None
    def __init__(self, frame):
        self.frame = frame
        self.__lp = None

    def __repr__(self):
        if hasattr(self, '_r'):
            return '...'
        self._r = True
        try:
            return f'locals: {", ".join(f"{k}={v!r}" for k, v in self.items())}'
        finally:
            del self._r

    @property
    def _lp(self):
        if self.__lp is None:
            addr = id(self.frame) + FrameType.__basicsize__ - base_size
            # get offset for locals array on `self.frame` object
            self.__lp = (py_object*len(self)).from_address(addr)
        return self.__lp

    def __getitem__(self, key):
        names = list(self)
        if key not in names:
            raise KeyError(key)
        try:
            return self._lp[names.index(key)]
        except ValueError:
            return Null

    def __setitem__(self, key, value):
        names = list(self)
        if key not in names:
            raise KeyError(key)
        del self[key]
        if value is not Null:
            Py_INCREF(value)
            self._lp[names.index(key)] = value

    def __delitem__(self, key):
        names = list(self)
        if key not in names:
            raise KeyError(key)
        idx = names.index(key)
        try:
            Py_DECREF(self._lp[idx])
        except ValueError:
            pass
        cast(self._lp, (c_void_p*len(self)))[idx] = None

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

(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)['locals'] = lambda:sys._getframe(1).f_locals

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
