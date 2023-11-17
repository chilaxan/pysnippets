BYTES_HEADER = bytes.__basicsize__ - 1
PTR_SIZE = tuple.__itemsize__
ENDIAN = ['big','little'][memoryview(b'\1\0').cast('h')[0]&0xff]

Py_TPFLAGS_VALID_VERSION_TAG = 1 << 19
Py_TPFLAGS_IMMUTABLETYPE = 1 << 8 # 3.10
Py_TPFLAGS_HEAPTYPE = 1 << 9

def sizeof(obj):
    return type(obj).__sizeof__(obj)

def make_getmem():
    load_addr = type(m:=lambda n,s:lambda v:s(v)or n)(
        (M:=m.__code__).replace(
            co_code=b'\x88'+M.co_code[1:]
        ),{}
    )(r:=iter(range(2**63-1)),r.__setstate__)

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
    cls_mem = getmem(id(cls), sizeof(cls), 'P')
    flags = cls.__flags__
    flag_offset = [*cls_mem].index(flags)
    if not cls.__flags__ & Py_TPFLAGS_VALID_VERSION_TAG:
        return
    for subcls in type(cls).__subclasses__(cls):
        PyType_Modified(subcls)
    cls_mem[flag_offset] &= ~Py_TPFLAGS_VALID_VERSION_TAG

def get_structs(htc=type('',(),{'__slots__':()})):
    htc_mem = getmem(id(htc), sizeof(htc), 'P')
    last = None
    for ptr, idx in sorted([(ptr, idx) for idx, ptr in enumerate(htc_mem)
            if id(htc) < ptr < id(htc) + sizeof(htc)]):
        if last:
            offset, lp = last
            yield offset, ptr - lp
        last = idx, ptr

def allocate_structs(cls):
    cls_mem = getmem(id(cls), sizeof(cls), 'P')
    for offset, size in get_structs():
        cls_mem[offset] = cls_mem[offset] or alloc(size)
    for subcls in type(cls).__subclasses__(cls):
        allocate_structs(subcls)
    return cls_mem

cache = {}
hooks = {}

def call_unprotected(func, cls, *args):
    cls_mem = allocate_structs(cls)
    flags = cls.__flags__
    flag_offset = [*cls_mem].index(flags)
    try:
        cls_mem[flag_offset] |= Py_TPFLAGS_HEAPTYPE
        cls_mem[flag_offset] &= ~Py_TPFLAGS_IMMUTABLETYPE
        func(cls, *args)
    finally:
        cls_mem[flag_offset] = flags
        PyType_Modified(cls)

def hook(cls, name=None, attr=None):
    def wrapper(attr):
        nonlocal name
        name = name or attr.__name__
        sentinel = object()
        old_val = cache.setdefault(cls,{}).get(name, sentinel)
        if old_val is not sentinel or hooks.get(cls, {}).get(name):
            raise RuntimeError(f'cannot re-hook {cls.__name__}.{name}')
        try:
            orig_value = cache.setdefault(cls,{})[name] = getattr(cls, name)
        except AttributeError:
            orig_value = sentinel
        if callable(attr):
            def hwrapper(*args, **kwargs):
                if not hwrapper.enabled:
                    if orig_value is not sentinel:
                        return orig_value(*args, **kwargs)
                    else:
                        return NotImplemented
                try:
                    hwrapper.enabled = False
                    return attr(*args, **kwargs)
                finally:
                    hwrapper.enabled = True
            hwrapper.enabled = True
            hooks.setdefault(cls, {})[name] = hwrapper
            call_unprotected(setattr, cls, name, hwrapper)
        else:
            call_unprotected(setattr, cls, name, attr)
        return attr
    if attr is None:
        return wrapper
    else:
        return wrapper(attr)

def restore_attr(cls, name):
    try:
        call_unprotected(setattr, cls, name, cache[cls].pop(name))
        if name in hooks.get(cls,{}):
            del hooks[cls][name]
    except KeyError:
        raise RuntimeError(f'{cls.__name__}.{name} not in cache')

def remove_attr(cls, name):
    call_unprotected(delattr, cls, name)
