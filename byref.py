import sys, dis

from asm_hook import hook
from ctypes import pythonapi, py_object, c_void_p
import f_locals # enable f_locals being writeable
from functools import wraps

# needed to hook into `STORE_GLOBAL` opcode
@hook(pythonapi.PyDict_SetItem, argtypes=[py_object]*3, restype=c_void_p)
def pydict_setitemhook(mp, key, val):
    mp[key] = val

def find_segments(co_code, idx, end_size):
    # take in set of opcodes and final stack size
    # determine segments of code for each final stack item
    stack_size = 0
    isjump = [*dis.hasjabs, *dis.hasjrel].__contains__
    segments = []
    seg = bytearray()
    seg_marker = 0
    while isjump(co_code[idx]) or stack_size != end_size:
        opcode = co_code[idx]
        oparg = co_code[idx + 1]
        seg[:] = bytes([opcode, oparg]) + seg
        jump = False if isjump(opcode) else None
        change = dis.stack_effect(opcode, oparg if opcode >= dis.HAVE_ARGUMENT else None, jump=jump)
        stack_size += change
        seg_marker += change
        idx -= 2
        if seg_marker == 1 and not isjump(co_code[idx]):
            segments.append(seg)
            seg = bytearray()
            seg_marker = 0
    return list(reversed(segments))

class magic_globals(dict):
    def __init__(self, mp):
        self.o_mp = mp
        self.mlocs = {}
        self.mglobs = {}
        super().__init__(mp)

    def _register_frame(self, frame):
        self._frame = frame

    def _register_local(self, mkey, idx):
        self.mlocs[mkey] = self._frame.f_code.co_varnames[idx]

    def _register_global(self, mkey, idx):
        self.mglobs[mkey] = self._frame.f_code.co_names[idx]

    def _clear_registry(self):
        del self._frame
        self.mlocs.clear()
        self.mglobs.clear()

    def __setitem__(self, key, val):
        if isinstance(key, str) and key[0] == '!':
            key = key[1:]
            if key in self.mlocs:
                self._frame.f_locals[self.mlocs[key]] = val
            elif key in self.mglobs:
                self._frame.f_globals[self.mglobs[key]] = val
            else:
                raise RuntimeError('Byref Var did not recieve direct reference')
        else:
            self.o_mp[key] = val

    def __getitem__(self, key):
        if isinstance(key, str) and key[0] == '!':
            key = key[1:]
            if key in self.mlocs:
                return self._frame.f_locals[self.mlocs[key]]
            elif key in self.mglobs:
                return self._frame.f_globals[self.mglobs[key]]
            else:
                raise RuntimeError('Byref Var did not recieve direct reference')
        return self.o_mp[key]

class Byref:
    def __init__(self, typ=None):
        self.typ = typ

    def __getitem__(self, ntyp):
        return self.__class__(ntyp)

    def __call__(self, func):
        mapping = func.__annotations__
        varnames = func.__code__.co_varnames
        pairs = {name: mapping.get(name) for name in varnames}
        for name, o in pairs.items():
            if isinstance(o, Byref):
                mapping[name] = o.typ
        orig_globals = func.__globals__
        co_code = bytearray(func.__code__.co_code)
        names = []
        for (i, (op, arg)) in enumerate(zip(co_code[::2], co_code[1::2])):
            opname = dis.opname[op]
            if opname in ['LOAD_FAST', 'STORE_FAST', 'DELETE_FAST'] and (dr := pairs.get(name := varnames[arg])):
                if f'!{name}' not in names:
                    names.append(f'!{name}')
                i *= 2
                co_code[i] = dis.opmap[opname.split('_')[0] + '_GLOBAL']
                co_code[i+1] = len(func.__code__.co_names) + names.index(f'!{name}')
        ncode = func.__code__.replace(co_code=bytes(co_code), co_names=func.__code__.co_names + tuple(names))
        nfunc = type(func)(ncode, magic_globals(orig_globals), None, func.__defaults__)
        @wraps(nfunc)
        def wrapper(*a, **k):
            caller_frame = sys._getframe(1)
            nfunc.__globals__._register_frame(caller_frame)
            idx = caller_frame.f_lasti
            co_code = caller_frame.f_code.co_code
            opname = dis.opname[co_code[idx]]
            oparg = co_code[idx + 1]
            if opname == 'CALL_FUNCTION':
                segments = find_segments(co_code, idx - 2, oparg)
            elif opname == 'CALL_FUNCTION_EX':
                # does not work if kwargs are present (fml edge cases)
                seg, *kwargs = find_segments(co_code, idx - 2, oparg + 1)
                del seg[-2:] # delete LIST_TO_TUPLE
                if seg[0] == dis.opmap['BUILD_LIST']:
                    raise RuntimeError('Byref Var must come before expanding postional argumets')
                while seg[-2] == dis.opmap['LIST_EXTEND']:
                    del seg[-2:] # delete LIST_EXTEND
                    del seg[-len(*find_segments(seg, len(seg) - 2, 1)):]
                oparg = seg[-1]
                del seg[-2:] # delete BUILD_LIST
                if not seg:
                    segments = []
                else:
                    segments = find_segments(seg, len(seg) - 2, oparg)
                if kwargs:
                    breakpoint()
            elif opname == 'CALL_FUNCTION_KW':
                # does not work if args are present additional to the kwargs (fml edge cases)
                segments = find_segments(co_code, idx - 2, oparg + 1)[:-1]
            for (varname, o), seg in zip(pairs.items(), segments):
                if len(seg) == 2 and isinstance(o, Byref):
                    op, arg = seg
                    if op in [dis.opmap['LOAD_GLOBAL'], dis.opmap['LOAD_NAME']]:
                        nfunc.__globals__._register_global(varname, arg)
                    elif op == dis.opmap['LOAD_FAST']:
                        nfunc.__globals__._register_local(varname, arg)
                    else:
                        raise RuntimeError('Byref Var did not recieve direct reference')
                elif isinstance(o, Byref):
                    raise RuntimeError('Byref Var did not recieve direct reference')
            try:
                return nfunc(*a, **k)
            finally:
                nfunc.__globals__._clear_registry()
        return wrapper

byref = Byref()

@byref
def inc(ref_x: byref):
    ref_x += 1

a = 0
inc(a)
print(a)
