import gc, ctypes
def get_dict(typ):
    return gc.get_referents(typ.__dict__)[0]

mp_dict = get_dict(memoryview)

def getmem(addr, size):
    return (ctypes.c_char*size).from_address(addr)

@classmethod
def from_address(cls, addr, size, fmt='c'):
    return cls(getmem(addr, size)).cast('c').cast(fmt)

mp_dict['from_address'] = from_address
