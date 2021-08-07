from ctypes import py_object, c_char
import atexit, builtins, sys, dis, random

def builtinexc(exc, depth=1):
    frame = sys._getframe(1 + depth)
    addr = id(frame.f_code.co_code) + bytes.__basicsize__ - 1
    mem = (c_char * len(frame.f_code.co_code)).from_address(addr)
    mem[frame.f_lasti + 2:frame.f_lasti + 4] = bytes([dis.opmap['RAISE_VARARGS'], 1])
    return exc

def maybe_get(dct, name):
    if name == 'Maybe':
        return random.random() < 0.5
    else:
        return builtinexc(NameError(f'name {name!r} is not defined'), 2)

def maybe_set(dct, name, value):
    if name != 'Maybe':
        return True
    raise SyntaxError(f'cannot assign to Maybe')

def maybe():
    g = sys._getframe(1).f_globals
    tp_base = py_object.from_address(id(g) + sizeof(c_void_p))
    class maybe_dict:pass
