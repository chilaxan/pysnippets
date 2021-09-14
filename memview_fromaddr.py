import gc, ctypes
def find(obj, typ):
    for o_obj in gc.get_objects():
        if isinstance(o_obj, typ) and obj==o_obj:
            return o_obj

mp_dict = find(memoryview.__dict__, dict)

def getmem(addr, size):
    return (ctypes.c_char*size).from_address(addr)

@classmethod
def from_address(cls, addr, size, fmt='c'):
    return cls(getmem(addr, size)).cast('c').cast(fmt)

mp_dict['from_address'] = from_address
