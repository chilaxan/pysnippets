BYTES_HEADER = bytes.__basicsize__ - 1 # constant value, gives offset into bytes->ob_sval array
PTR_SIZE = tuple.__itemsize__ # constant value, size of pointer (4 or 8)
ENDIAN = ['little','big'][1%memoryview(b'\1\0').cast('h')[0]]
# ^ constant value, obtains the endian for the system, creates a 2 byte array, casts to a short (2 byte number)
# this number is dependent on the endian, so you can use it to detect the endian of the system.
# big: 256, little: 1

## Constant Flag Values (see object.h)
Py_TPFLAGS_VALID_VERSION_TAG = 1 << 19
Py_TPFLAGS_IMMUTABLETYPE = 1 << 8 # 3.10
Py_TPFLAGS_HEAPTYPE = 1 << 9

def sizeof(obj):
    '''sizeof that works on arbitrary objects'''
    return type(obj).__sizeof__(obj)

def make_getmem():
    '''closure based exploit to allow the loading of arbitrary addresses'''

    # constructs a function that returns a function
    # inner function has 2 closure variables
    # the outer function has one opcode (LOAD_CLOSURE) changed to (LOAD_DEREF)
    # this makes the inner function load addressof(n) + (PTR_SIZE * 3) as a python object
    # in a range_iter object, this third value is a c long of the current index of the iterator
    # this index can be set using `__setstate__`
    # the resulting function `load_addr` sets this index to an address, and then loads `n`
    # loading `n` actually loads addressof(n) + (PTR_SIZE * 3), allowing for an arbitrary address to be loaded
    load_addr = type(m:=lambda n,s:lambda v:s(v)or n)(
        (M:=m.__code__).replace(
            co_code=b'\x88'+M.co_code[1:]
        ),{}
    )(r:=iter(range(2**63-1)),r.__setstate__)

    # constructs a fake bytearray that points to the entire address space
    memory_backing = bytes(PTR_SIZE) \
                   + id(bytearray).to_bytes(PTR_SIZE, ENDIAN) \
                   + bytes([255] * (PTR_SIZE - 1) + [127]) \
                   + bytes(PTR_SIZE * 4)

    memory = memoryview(load_addr(id(memory_backing) + BYTES_HEADER))

    def getmem(start, size, fmt='c', _=memory_backing):
        return memory[start:start + size].cast(fmt)

    # returns a function that generates a rw segment of memory that points to `start`
    return getmem

getmem = make_getmem()

def alloc(size, _storage=[]):
    '''allocates size inside a bytes object, then returns the address of the `ob_sval` array'''
    _storage.append(bytes(size))
    return id(_storage[-1]) + BYTES_HEADER

def PyType_Modified(cls):
    '''pure python implementation of `PyType_Modified` (see typeobject.c)'''
    cls_mem = getmem(id(cls), sizeof(cls), 'L')
    flags = cls.__flags__
    flag_offset = cls_mem.tolist().index(flags)
    if not cls.__flags__ & Py_TPFLAGS_VALID_VERSION_TAG:
        return
    for subcls in type(cls).__subclasses__(cls):
        PyType_Modified(subcls)
    cls_mem[flag_offset] &= ~Py_TPFLAGS_VALID_VERSION_TAG

def get_structs(htc=type('',(),{'__slots__':()})):
    '''generates the offset and size of internal `tp_as_*` structs'''
    htc_mem = getmem(id(htc), sizeof(htc), 'L')
    last = None
    for ptr, idx in sorted([(ptr, idx) for idx, ptr in enumerate(htc_mem)
            if id(htc) < ptr < id(htc) + sizeof(htc)]):
        if last:
            offset, lp = last
            yield offset, ptr - lp
        last = idx, ptr

cache = {}
def orig(*args, **kwargs):
    '''attempts to retrieve and call the cached original implementation'''
    try:raise
    except Exception as e:
        frame = e.__traceback__.tb_frame
    while frame:
        addr = id(frame.f_code)
        if addr in cache:
            return cache.get(addr)(*args, **kwargs)
        frame = frame.f_back
    raise RuntimeError('original implementation not found')

def hook(cls, name=None, attr=None):
    '''where the magic happens'''
    def wrapper(attr):
        nonlocal name
        name = name or attr.__name__
        cls_mem = getmem(id(cls), sizeof(cls), 'L') # gets a writable reference to the class memory
        for offset, size in get_structs():
            if not cls_mem[offset]:
                cls_mem[offset] = alloc(size) # allocates any structs that are missing
        flags = cls.__flags__ # store original flags
        flag_offset = cls_mem.tolist().index(flags)
        if hasattr(attr, '__code__') and hasattr(cls, name):
            cache[id(attr.__code__)] = getattr(cls, name) # add original implementationt to the cache
        try:
            cls_mem[flag_offset] |= Py_TPFLAGS_HEAPTYPE # set `Py_TPFLAGS_HEAPTYPE` flag to 1
            cls_mem[flag_offset] &= ~Py_TPFLAGS_IMMUTABLETYPE # set`Py_TPFLAGS_IMMUTABLETYPE` to 0
            setattr(cls, name, attr) # attempt to set attribute
        finally:
            cls_mem[flag_offset] = flags # set flags back to original
            PyType_Modified(cls) # signal to subclasses that updates have been made
        return attr
    if attr is None:
        return wrapper
    else:
        return wrapper(attr)
