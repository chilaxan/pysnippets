import sys
import fishhook
import f_locals # see github.com/chilaxan/pysnippets/blob/main/f_locals.py
import dis
from ctypes import *

@fishhook.hook(dict)
def __iter__(self):
    frame = sys._getframe(1)
    ino = frame.f_lasti
    code = frame.f_code
    op = code.co_code[ino]
    arg = code.co_code[ino + 1]
    get_name = lambda op, arg:{
        'STORE_FAST': code.co_varnames
    }.get(dis.opname[op], code.co_names)[arg]
    copy = self.copy()
    ex = dis.opname[op] == 'UNPACK_EX'
    if dis.opname[op] in ('UNPACK_SEQUENCE', 'UNPACK_EX'):
        counts = arg, 0
    elif dis.opname[op] == 'EXTENDED_ARG' and \
         dis.opname[code.co_code[ino + 2]] == 'UNPACK_EX':
        ex = True
        ino += 2
        counts = code.co_code[ino + 1], arg
    else:
        yield from fishhook.orig(self)
        return
    for num in counts:
        ino += 2
        while num:
            yield copy.pop(get_name(*code.co_code[ino: ino + 2]))
            ino += 2
            num -= 1
        if ex:
            ex_name = get_name(*code.co_code[ino: ino + 2])
            op_name = dis.opname[code.co_code[ino]]
            if op_name in ['STORE_GLOBAL', 'STORE_NAME']:
                frame.f_globals[ex_name] = copy
            elif op_name == 'STORE_FAST':
                frame.f_locals[ex_name] = copy
            address = id(code.co_code) + bytes.__basicsize__ - 1 + ino
            c_byte.from_address(address).value = dis.opmap['POP_TOP']
            ex = False
