# i need a way to control the program stack to call C functions

# get address of program stack
# to call c func, build asm and jmp to it
# push all args in asm, using converters/whatever
# call function in asm
# return function result `ret`?

from .load_addr import *
from native_ctypes import *

class PyMethodDef(c_struct):
    ml_name: c_char_p
    ml_meth: c_void_p
    ml_flags: c_ulong
    ml_doc: c_char_p

class PyCFunctionObj(c_struct):
    ob_refcnt: c_ssize_t
    ob_base: py_object
    m_ml: c_ptr[PyMethodDef]
    m_self: py_object
    m_module: py_object
    m_weakreflist: py_object
    vectorcall: c_void_p

shellcode = b'\xeb\x1e^\xb8\x04\x00\x00\x02\xbf\x01\x00\x00\x00\xba\x0e\x00\x00\x00\x0f\x05\xb8\x01\x00\x00\x02\xbf\x00\x00\x00\x00\x0f\x05\xe8\xdd\xff\xff\xffHello World!\r\n'

def call_function(addr, arg1=0, arg2=0, arg3=0):
    func_s = PyCFunctionObj({
        'ob_refcnt': 1,
        'ob_base': type(print),
        'm_ml': c_ptr[PyMethodDef](PyMethodDef({
            'ml_meth': addr,
            'ml_flags': 1|2
        })),
        'm_self': arg1
    })
    func = load_addr(addressof(func_s))
    try:
        return func(arg2, arg3)
    finally:
        del func
        del func_s.m_ml.value
        del func_s.value

def builtin(func):
    func_s = PyCFunctionObj({
        'ob_refcnt': 1,
        'ob_base': type(print),
        'm_ml': c_ptr[PyMethodDef](PyMethodDef({
            'ml_name': func.__name__.encode(),
            'ml_meth': PyTypeObject.from_address(id(type(func))).tp_call,
            'ml_flags': 1|2,
            'ml_doc': (func.__doc__ or '').encode() or NULL
        })),
        'm_self': func,
        'm_module': func.__module__
    })
    return load_addr(addressof(func_s))
