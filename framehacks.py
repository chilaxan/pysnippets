#SUPPORTS# <= 3.9 (Tmeta)

import sys, dis
try:
    from native_ctypes import getmem
except:
    from ctypes import c_char
    def getmem(addr, size):
        return memoryview((c_char*size).from_address(addr)).cast('B')

'''
A collection of various weird code that tend to use stack frames in weird ways
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
def builtinexc(exc, level=0):
    frame = sys._getframe(2 + level)
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

import gc

class magic:
    def __length_hint__(self):
        return 1
    def __iter__(self):
        for obj in gc.get_objects():
            if type(obj) == tuple and len(obj) == 1:
                try:1 in obj
                except SystemError:
                    yield obj
                    break

weird = tuple(magic())

# fishhook research

# A-E are unknown size arrays

'''
(PyHeapTypeObject) [
  (PyTypeObject) [
  ...
  -> A
  ...
  -> C
  -> B
  -> D
  ...
  -> E
  ]
  A
  B
  C
  D
  E
  ...
]
'''

# 1. Collect ptr values to get starting addresses of A-E by looking for pointers that direct within PyHeapTypeObject
from ctypes import (
    sizeof,
    c_void_p,
    c_char
)

basic_size = sizeof(c_void_p)

def mem(addr, size):
    return (c_char*size).from_address(addr)

class HeapTypeObj:
    __slots__ = ()

size = type(HeapTypeObj).__sizeof__(HeapTypeObj)
static_size = type.__sizeof__(type)
cls_mem = mem(id(HeapTypeObj), size).raw
address = id(HeapTypeObj)
pointers = [(offset, ptr) for offset, ptr in enumerate(memoryview(cls_mem).cast('l'))
                if address < ptr < address + len(cls_mem)]

# 2. Get Differences between ptr[B]-ptr[A], ... to get sizes
sizes = []
last_addr = None
for offset, ptr in sorted(pointers, key=lambda i:i[1]):
    if last_addr is not None:
        sizes.append(ptr - last_addr)
    last_addr = ptr

sizes.append(last_addr - ptr + len(cls_mem))

# 3. We now know the offsets and sizes of ptr[A-E] in PyTypeObject
structs = [(0, static_size)] \
        + [(offset, size) for (offset, _), size in zip(pointers, sizes)]

# 4. Now comes the fun part
# see fishhook

import dis, sys

old_import = __builtins__.__import__

def my_import(name, globals=None, locals=None, fromlist=(), level=0):
    try:
        frame = sys._getframe(1)
    except:
        return old_import(name, globals, locals, fromlist, level)
    loc = frame.f_globals["__name__"]
    code = frame.f_code
    co_code = code.co_code
    lasti = frame.f_lasti
    next_op = dis.opname[co_code[lasti + 2]]
    next_arg = co_code[lasti + 3]
    fl = ', '.join(fromlist) + ' from ' if fromlist else ''
    if 'STORE_' in next_op:
        if next_op in ['STORE_GLOBAL', 'STORE_NAME']:
            print(f'importing {fl}{name} as {code.co_names[next_arg]} in {loc}.{code.co_name}')
        else:
            print(f'importing {fl}{name} as {code.co_varnames[next_arg]} in {loc}.{code.co_name}')
    else:
        print(f'importing {fl}{name} in {loc}.{code.co_name}')
    return old_import(name, globals, locals, fromlist, level)

__builtins__.__import__ = my_import

import os

import sys
import dis

class name_aware:
    def __init__(self):
        frame = None
        level = 1
        while frame is None or 'STORE_' not in (op:=dis.opname[
            (bc:=(code:=frame.f_code).co_code)[(idx:=frame.f_lasti + 2)]
        ]):
            try:
                frame = sys._getframe(level)
            except ValueError:
                self.__inst_name__ = None
                return
            level += 1
        if op in ['STORE_GLOBAL', 'STORE_NAME']:
            self.__inst_name__ = code.co_names[bc[idx + 1]]
        elif op == 'STORE_FAST':
            self.__inst_name__ = code.co_varnames[bc[idx + 1]]
        else:
            self.__inst_name__ = None

    def __repr__(self):
        if self.__inst_name__:
            return f'{self.__inst_name__} = {super().__repr__()}'
        else:
            return super().__repr__()


class a(name_aware):pass

class b(name_aware):
    def __init__(self, arg):
        ...
        super().__init__()

load_addr = type(m:=lambda n,s:lambda v:s(v)or n)(
    (M:=m.__code__).replace(
        co_code=b'\x88'+M.co_code[1:]
    ),{}
)(r:=iter(range(2**63-1)),r.__setstate__)

from ctypes import pythonapi, py_object
import sys
PyType_Modified = pythonapi.PyType_Modified
PyType_Modified.argtypes = [py_object]

load_off3 = type(m:=lambda n:(lambda:n)())(
    (M:=m.__code__).replace(
        co_code=b'\x88'+M.co_code[1:]
    ),{}
)

old_format = str.format
def new_format(self, *args, **kwargs):
    if args:
        return old_format(self, *args, **kwargs)
    f = sys._getframe(1)
    return eval('f' + repr(self), f.f_globals, {**f.f_locals, **kwargs})

load_off3(str.__dict__)['format'] = new_format
PyType_Modified(str)

def get_idx(col, val):
    try:
        return col.index(val)
    except ValueError:
        return None

def replace_consts(*vals):
    def wrapper(func):
        consts = [*func.__code__.co_consts]
        for oval, nval in vals:
            if oval in func.__code__.co_consts:
                consts[func.__code__.co_consts.index(oval)] = nval
        func.__code__ = func.__code__.replace(
            co_consts=tuple(consts)
        )
        return func
    return wrapper

@replace_consts((None, 1))
def test():
    print('yeet')

print(test())

def inject_constant(code, name, val):
    byc = code.co_code
    new_inst = bytes([100, len(code.co_consts)])
    for op, names in [(116, code.co_names), (124, code.co_varnames)]:
        if name in names:
            idx = names.index(name)
            byc = byc.replace(bytes([op, idx]), new_inst)
    return code.replace(co_consts=code.co_consts + (val,), co_code=byc)

def isvalidptr(addr, size=1):
    import os
    r, w = os.pipe()
    try:
        return os.write(w, getmem(addr,size)) == size
    except OSError:
        return False
    finally:
        os.close(r)
        os.close(w)

def get_cls_dict(cls, E=type('',(),{'__eq__':lambda s,o:o})()):
    return cls.__dict__ == E

import typing

@lambda c:c()
class __annotations__(dict):
    def __setitem__(self, name, value):
        if isinstance(value, typing.Callable):
            try:
                func = globals()[name]
                args = list(value.__args__)
                annots = func.__annotations__
                annots['return'] = args.pop()
                for varname in func.__code__.co_varnames:
                    if not args: break
                    annots[varname] = args.pop(0)
            except:pass
        super().__setitem__(name, value)

f: typing.Callable[int, str] = lambda x: chr(x)

current_frame = next(g:=(g.gi_frame.f_back for()in[()]))

getframe=lambda i=0:[*(g:=(f:=g.gi_frame.f_back for()in[()]))]and[f:=f.f_back for()in[()]*(i+1)][i]


s=lambda x,r=range:x.translate([*r(65),*r(97,123),*r(91,97),*r(65,91)])

def s():
    v=None
    while 1:
        v = (yield v).translate([*(r:=range)(65),*r(97,123),*r(91,97),*r(65,91)])

(s:=s().send)(None)

class frame:
    def __init__(self, f_back):
        self.f_back = f_back

def new_frame():
    f = None
    while 1:
        f = frame(f)
        yield f

new_frame = new_frame().__next__


from dis import dis
dis("a = b = c = d = 10")
print()
dis("d = (c := (b := (a := 10)))")

# Use After Free in io.BufferedReader
io = open.__self__

class UAF(io._RawIOBase):
    def readinto(self, buf):
        self.buf = buf.cast('P')
    def readable(self):
        return True

u = UAF()
b = io.BufferedReader(u, 56)
b.read(1) # store view of buffer on `u` (calls `readinto`)
# use `__init__` to free internal buffer instead of relying on GC
u.view = b.__init__(u) or bytearray()
# at this point, if successful, `u.buf` is the memory that backs `u.view`
u.buf[2] = (pow(2, tuple.__itemsize__ * 8) // 2) - 1
u.memory = memoryview(u.view)

def getmem(addr, size, fmt='c'):
    return u.memory[addr: addr + size].cast(fmt)

def load_addr(addr):
    T = (None,)
    offset = id(T) + tuple.__basicsize__
    container = getmem(id(T) + tuple.__basicsize__, tuple.__itemsize__, 'P')
    try:
        container[0] = addr
        return T[0]
    finally:
        container[0] = id(None)

print(load_addr(id(1)))

import sys, inspect
def get_signature(frame):
    argvals = inspect.getargvalues(frame)
    args = tuple(argvals.locals.get(name) for name in argvals.args if name in (func.__kwdefaults__) or {}) \
            + argvals.locals.get(argvals.varargs) if argvals.varargs else ()

    kwargs = argvals.locals.get(argvals.keywords) if argvals.keywords else {}
    for name in argvals.args:
        if name in func.__kwdefaults__:
            kwargs[name] = argvals.locals.get(name)
    return tuple(map(type, args)), tuple((k, type(v)) for k, v in kwargs.items())

def dispatch(*args, **kwargs):
    def dispatch_inner(func):
        func.sig = (args, tuple(kwargs.items()))
        return func
    return dispatch_inner

class DispatchDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatch = {}
    def __setitem__(self, key, value):
        if not hasattr(value, 'sig'):
            if key in self.dispatch:
                self.dispatch[key]['default'] = value
            else:
                return super().__setitem__(key, value)
        ftbl = self.dispatch.setdefault(key, {})
        ftbl[value.sig] = value
        def inner(*a, **k):
            args, kwargs = get_signature(sys._getframe())
            try:
                func = ftbl[args[1:], kwargs]
            except KeyError:
                func = ftbl['default']
            return func(*a, **k)
        super().__setitem__(key, inner)

class Dispatchable(type):
    def __prepare__(*args):
        return DispatchDict()

class Foo(metaclass=Dispatchable):
    @dispatch(int, int)
    def method(self, a, b):
        print(a - b)

    @dispatch(str, str)
    def method(self, a, b):
        print(a + b)

    def method(self, a, b):
        print('default case')
