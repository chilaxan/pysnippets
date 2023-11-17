#SUPPORTS# <= 3.9

# gadget.__code__ = (gadget:=lambda v,*s:(v,v,v)).__code__.replace(co_code=b'|\0|\1p\12\x88\0n\4\\\1\x89\0S\0')

# freevars = f->f_fastlocals + co->co_nlocals
# this means if co->co_nlocals is 0, freevars points to the top of the frame.stack
# LOAD_DEREF(n - co_nlocals) pushes fastlocal[co_nlocals-n] as obj->cell_contents
# LOAD_DEREF(n + co_nfreevars) pushes frame.stack[n] as obj->cell_contents
# LOAD_CLOSURE(n + co_nfreevars) push frame.stack[n]

import dis
gadget = lambda v,*s:None # freevars = frame.stack
gadget.__code__ = gadget.__code__.replace(
    co_stacksize=3,
    co_nlocals=0,
    co_code=bytes([
        dis.opmap['LOAD_FAST'], 0,              # 00: frame.stack[0] = v
        dis.opmap['LOAD_FAST'], 1,              # 02: frame.stack[1] = s
        dis.opmap['JUMP_IF_TRUE_OR_POP'], 10,   # 04: lasti = 10 if frame.stack[1] else (frame.stack[1] = NULL)
        dis.opmap['LOAD_DEREF'], 0,             # 06: frame.stack[0] = freevars[0]->cell_contents
        dis.opmap['JUMP_FORWARD'], 4,           # 08: lasti += 6
        dis.opmap['UNPACK_SEQUENCE'], 1,        # 10: frame.stack[1] = frame.stack[1][0];
        dis.opmap['STORE_DEREF'], 0,            # 12: freevars[0]->cell_contents = frame.stack[1]; frame.stack[1] = NULL
        dis.opmap['RETURN_VALUE'], 0            # 14: return frame.stack[0]; frame.stack[0] = NULL
    ])
)

x = (0,)
gadget(list.__setitem__, tuple)
list.__setitem__((x, 1, 2, 3), 3, x)
gadget(list.__setitem__, list)
print(x)

import dis
load = lambda *a:None # freevars = frame.stack
load.__code__ = load.__code__.replace(
    co_stacksize=4,
    co_nlocals=0,
    co_code=bytes([
        dis.opmap['BUILD_LIST'], 0,     # 00: frame.stack[0] = list()
        dis.opmap['LOAD_FAST'], 0,      # 02: frame.stack[1] = a
        dis.opmap['GET_ITER'], 0,       # 04: frame.stack[1] = iter(a)
        dis.opmap['FOR_ITER'], 8,       # 06: frame.stack[2] = next(frame.stack[1]) or (frame.stack[1] = NULL; lasti += 10)
        dis.opmap['LOAD_DEREF'], 2,     # 08: frame.stack[3] = freevars[2]->cell_contents
        dis.opmap['LIST_APPEND'], 3,    # 10: frame.stack[0].append(frame.stack[3]); frame.stack[3] = NULL
        dis.opmap['POP_TOP'], 0,        # 12: frame.stack[2] = NULL
        dis.opmap['JUMP_ABSOLUTE'], 6,  # 14: lasti = 6
        dis.opmap['LIST_TO_TUPLE'], 0,  # 16: frame.stack[0] = tuple(frame.stack[0])
        dis.opmap['RETURN_VALUE'], 0    # 18: return frame.stack[0]; frame.stack[0] = NULL
    ])
)
