#SUPPORTS# <= 3.9

import sys
from ctypes import c_char

BYTES_OFFSET = bytes.__basicsize__ - 1

def getmem(addr, size):
    return (c_char * size).from_address(addr)

fix_ops = [None, None, None]

class state:
    def __init__(self, anchor):
        self.anchor = anchor

    def __getattr__(self, attr):
        return self.anchor.l_state.get(attr) or self.anchor.g_state[attr]

class anchor:
    def __init__(self):
        frame = sys._getframe(1)
        if None not in fix_ops:
            idx, size, ops = fix_ops
            getmem(id(frame.f_code.co_code) + BYTES_OFFSET + idx, size)[:] = ops
        self.g_state = frame.f_globals.copy()
        self.l_state = frame.f_locals.copy()
        self.location = frame.f_lasti - 2

def backstep(anchor, depth=1):
    frame = sys._getframe(depth)
    co_code = frame.f_code.co_code
    inj_idx = frame.f_lasti + 2
    fix_ops[:] = inj_idx, 2, co_code[inj_idx: inj_idx + 2]
    getmem(id(co_code) + BYTES_OFFSET + inj_idx, 2)[:] = bytes([114, anchor.location])

i = 0
a = anchor()
i += 1
if i < 5:
    backstep(a)
print(i)
