from ctypes import py_object, c_char
import atexit, builtins, sys, dis

def builtinexc(exc, depth=1):
    frame = sys._getframe(1 + depth)
    addr = id(frame.f_code.co_code) + bytes.__basicsize__ - 1
    mem = (c_char * len(frame.f_code.co_code)).from_address(addr)
    mem[frame.f_lasti + 2:frame.f_lasti + 4] = bytes([dis.opmap['RAISE_VARARGS'], 1])
    return exc

frame = sys._getframe()
while frame != None:
    ob_base_p = py_object.from_address(id(frame.f_globals) + 8)
    class cin_hook(dict):
        __slots__ = ()
        def __missing__(self, key, ob_base_p=ob_base_p, builtins=builtins):
            try:
                ob_base_p.value = builtins.dict
                if key == 'cin':
                    frame = sys._getframe(1)
                    f_code = frame.f_code
                    load_idx = shift_idx = frame.f_lasti + 2
                    while f_code.co_code[shift_idx] != dis.opmap['BINARY_RSHIFT']:
                        shift_idx += 2
                        if shift_idx >= len(f_code.co_code):
                            return input()
                    last_load = shift_idx - 2
                    instr = dis.opname[f_code.co_code[last_load]].replace('LOAD_', 'STORE_')
                    if instr == 'BINARY_SUBSCR':
                        instr = 'STORE_SUBSCR'
                    mem = (c_char * len(f_code.co_code)).from_address(id(f_code.co_code) + bytes.__basicsize__ - 1)
                    mem[last_load] = dis.opmap[instr]
                    mem[shift_idx: shift_idx + 2] = bytes([
                        dis.opmap['LOAD_CONST'], f_code.co_consts.index(None)
                    ])
                    return input()
                return builtins.__dict__[key]
            except KeyError as e:
                return builtinexc(NameError(f'name {e.args[0]!r} is not defined'), 1)
            finally:
                ob_base_p.value = __class__

    ob_base_p.value = cin_hook
    frame = frame.f_back
