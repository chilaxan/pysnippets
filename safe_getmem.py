BYTES_HEADER = bytes.__basicsize__ - 1
PTR_SIZE = tuple.__itemsize__
ENDIAN = ['big','little'][memoryview(b'\1\0').cast('h')[0]&0xff]

def sizeof(obj):
    return type(obj).__sizeof__(obj)

def align(v, m=PTR_SIZE):
    return ((v + m - 1) // m) * m

def getsize(fmt):
    size = 1
    while True:
        try:
            memoryview(bytes(size)).cast(fmt)
            return size
        except TypeError:
            size += 1

load_addr = type(m:=lambda n,s:lambda v:s(v)or n)(
    (M:=m.__code__).replace(
        co_code=b'\x88'+M.co_code[1:]
    ),{}
)(r:=iter(range(2**(PTR_SIZE*8-1)-1)),r.__setstate__)

memory_backing = bytes(PTR_SIZE) \
               + id(bytearray).to_bytes(PTR_SIZE, ENDIAN) \
               + bytes([255] * (PTR_SIZE - 1) + [127]) \
               + bytes(PTR_SIZE * 4)

memory = memoryview(load_addr(id(memory_backing) + BYTES_HEADER))

def getmem(start, size, fmt='c'):
    import os
    r, w = os.pipe()
    try:
        if os.write(w, memory[start:start + 1]) == 1:
            return memory[start:align(start + size, getsize(fmt))].cast(fmt)
    except OSError:pass
    finally:
        os.close(r)
        os.close(w)
    raise OSError('bad address') from None

import os
from ctypes import c_char
def check_addr(addr, size):
    r, w = os.pipe()
    try:
        if os.write(w, (c_char*size).from_address(addr)):
            return True
    except OSError as e:
        print(e)
        return False
    finally:
        os.close(r)
        os.close(w)