from asm_hook import hook
from native_ctypes import PyTypeObject
from ctypes import *
from _ctypes import PyObj_FromPtr
from framehacks import builtinexc

dict_struct = PyTypeObject.from_address(id(dict))
_FuncPtr = type(pythonapi.Py_IncRef)
dict_new = _FuncPtr(dict_struct.tp_new)
dict_init = _FuncPtr(dict_struct.tp_init)
dict_vectorcall = _FuncPtr(dict_struct.tp_vectorcall)

def protect(func):
    def new_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return builtinexc(e, 1)
    return new_func

@hook(dict_init, restype=c_int, argtypes=[py_object, c_void_p, c_void_p])
@protect
def hooked_dict_init(self, args, kwargs):
    print('dict_init called',
        '\n\targs:', PyObj_FromPtr(args) if args else 'NULL',
        '\n\tkwargs:', PyObj_FromPtr(kwargs) if kwargs else 'NULL')
    return dict_init(self, args, kwargs)

@hook(dict_new, restype=py_object, argtypes=[py_object, c_void_p, c_void_p])
@protect
def hooked_dict_new(typ, args, kwargs):
    print('dict_new called',
        '\n\targs:', PyObj_FromPtr(args) if args else 'NULL',
        '\n\tkwargs:', PyObj_FromPtr(kwargs) if kwargs else 'NULL')
    return dict_new(typ, args, kwargs)

@hook(pythonapi._PyDict_NewPresized, restype=py_object, argtypes=[c_ssize_t])
@protect
def hooked__PyDict_NewPresized(size):
    print('_PyDict_NewPresized called',
        '\n\tsize:', size)
    return pythonapi._PyDict_NewPresized(size)

@hook(dict_vectorcall, restype=py_object, argtypes=[py_object, POINTER(py_object), c_size_t, c_void_p])
@protect
def hooked_dict_vectorcall(typ, argv, argcf, kwnames):
    argc = argcf & ~(1 << (8 * sizeof(c_size_t) - 1))
    args = argv[:argc]
    print('dict_vectorcall',
        '\n\targs:', args,
        '\n\tkwargs:', {key:argv[argc + idx] for idx, key in enumerate(PyObj_FromPtr(kwnames))} if kwnames else 'NULL')
    return dict_vectorcall(typ, argv, argc, kwnames)
