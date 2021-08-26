TUPLE_HEADER = tuple.__basicsize__
BYTES_HEADER = bytes.__basicsize__ - 1
PTR_SIZE = tuple.__itemsize__
ENDIAN = ['little','big'][1%memoryview(b'\1\0').cast('h')[0]]

Py_TPFLAGS_VALID_VERSION_TAG = 1 << 19
Py_TPFLAGS_HEAPTYPE = 1 << 9

def sizeof(obj):
    return type(obj).__sizeof__(obj)

def make_getmem():
    def load_addr(a):
        m = lambda n:lambda:n
        m.__code__ = (M:=m.__code__).replace(
            co_consts=(c:=M.co_consts)+(r:=iter(range(a+1)),),
            co_code=M.co_code.replace(b'\x87\0',bytes([100,len(c)])),
        )
        return r.__setstate__(a) or m(0)()

    memory_backing = bytes(PTR_SIZE) \
                   + id(bytearray).to_bytes(PTR_SIZE, ENDIAN) \
                   + bytes([255] * (PTR_SIZE - 1) + [127]) \
                   + bytes(PTR_SIZE * 4)

    memory = memoryview(load_addr(id(memory_backing) + BYTES_HEADER))

    def getmem(start, size, fmt='c', _=memory_backing):
        return memory[start:start + size].cast(fmt)

    return getmem

getmem = make_getmem()

def alloc(size, _storage=[]):
    _storage.append(bytes(size))
    return id(_storage[-1]) + BYTES_HEADER

def PyType_Modified(cls):
    cls_mem = getmem(id(cls), sizeof(cls), 'L')
    flags = cls.__flags__
    flag_offset = cls_mem.tolist().index(flags)
    if not cls.__flags__ & Py_TPFLAGS_VALID_VERSION_TAG:
        return
    for subcls in type(cls).__subclasses__(cls):
        PyType_Modified(subcls)
    cls_mem[flag_offset] &= ~Py_TPFLAGS_VALID_VERSION_TAG

def get_structs(htc=type('',(),{'__slots__':()})):
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
    def wrapper(attr):
        nonlocal name
        name = name or attr.__name__
        cls_mem = getmem(id(cls), sizeof(cls), 'L')
        for offset, size in get_structs():
            if not cls_mem[offset]:
                cls_mem[offset] = alloc(size)
        flags = cls.__flags__
        flag_offset = cls_mem.tolist().index(flags)
        if hasattr(attr, '__code__') and hasattr(cls, name):
            cache[id(attr.__code__)] = getattr(cls, name)
        try:
            cls_mem[flag_offset] |= Py_TPFLAGS_HEAPTYPE
            setattr(cls, name, attr)
        finally:
            cls_mem[flag_offset] = flags
            PyType_Modified(cls)
        return attr
    if attr is None:
        return wrapper
    else:
        return wrapper(attr)
