import sys, dis
try:
    from native_ctypes import getmem
except:
    from ctypes import c_char
    def getmem(addr, size):
        return memoryview((c_char*size).from_address(addr)).cast('B')

'''
A collection of various weird code that tend to use frames in weird ways
'''

# breaks in larger files that have EXTENDED_ARG before the JUMP_IF_FALSE_OR_POP
# replace JUMP_IF_FALSE_OR_POP with NOP then
# scan until we hit COMPARE_OP (>) Followed by JUMP_FORWARD, ROT_TWO, POP_TOP
# replace those ops with ROT_TWO, ROT_THREE, CALL_FUNCTION(2), NOP
# This rearranges the stack to be [cls, T, args], then calls cls(T, args)
# and returns it

class Tmeta(type):
    def __lt__(cls, ocls):
        frame = sys._getframe(1)
        mem = getmem(id(frame.f_code.co_code) + bytes.__basicsize__ - 1, len(frame.f_code.co_code))
        instructions = [*dis.get_instructions(frame.f_code)]
        for idx, instruction in enumerate(instructions):
            if idx * 2 < frame.f_lasti:
                continue
            if instruction.opname == 'COMPARE_OP' and instruction.argval == '>':
                if instructions[idx+1].opname == 'JUMP_FORWARD':
                    if instructions[idx+2].opname == 'ROT_TWO':
                        if instructions[idx+3].opname == 'POP_TOP':
                            inj_code = bytes([
                                dis.opmap['ROT_TWO'], 0,
                                dis.opmap['ROT_THREE'], 0,
                                dis.opmap['CALL_FUNCTION'], 2,
                                dis.opmap['NOP'], 0,
                            ])
                            mem[frame.f_lasti] = dis.opmap['POP_TOP']
                            mem[frame.f_lasti + 2] = dis.opmap['NOP']
                            mem[idx * 2:idx * 2 + len(inj_code)] = inj_code
                            return cls

class Array(metaclass=Tmeta):
    def __init__(self, T, args):
        self.T = T
        self.args = args

    def __repr__(self):
        return f'{type(self).__name__}<{self.T.__name__}>{self.args}'

class HashMap(metaclass=Tmeta):
    def __init__(self, T, args):
        self.T = T
        self.args = args

    def __repr__(self):
        return f'{type(self).__name__}<({", ".join(t.__name__ for t in self.T)})>{self.args}'

a = Array<int>(1,2,3)
b = HashMap<(str, int)>{
    'a': 0,
    'b': 1
}

def f():
    v = Array<int>(1,2,3)
    print(v)

# the following allows for a function to emulate a C style exception
# removes the traceback of the function internals
# inject raise after upper function
# use as `return builtinexc(exc)`
def builtinexc(exc):
    frame = sys._getframe(2)
    mem = getmem(id(frame.f_code.co_code) + bytes.__basicsize__ - 1, len(frame.f_code.co_code))
    mem[frame.f_lasti + 2:frame.f_lasti + 4] = bytes([dis.opmap['RAISE_VARARGS'], 1])
    return exc

def test_builtinexc():
    return builtinexc(TypeError('testing'))

from ctypes import (
    pythonapi, POINTER, byref,
    c_int, c_wchar_p
)
import os

def rerun(*new_flags, keep_old=True):
    _argv = POINTER(c_wchar_p)()
    _argc = c_int()
    pythonapi.Py_GetArgcArgv(byref(_argc), byref(_argv))
    orig_argv = _argv[:_argc.value]
    if keep_old:
        orig_argv[1:1] = new_flags
        os.execv(orig_argv[0], orig_argv)
    else:
        os.execv(orig_argv[0], (orig_argv[0],) + new_flags)
