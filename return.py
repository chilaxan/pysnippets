BYTES_HEADER = bytes.__basicsize__ - 1
PTR_SIZE = tuple.__itemsize__
ENDIAN = ['big','little'][memoryview(b'\1\0').cast('h')[0]&0xff]

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

def getframe(level=0):
    try:raise
    except Exception as e:
        frame = e.__traceback__.tb_frame.f_back
        for () in [()] * level:
            frame = frame.f_back
        return frame

def Return(val):
    frame = getframe(1)
    offset = id(frame.f_code.co_code) + bytes.__basicsize__ + frame.f_lasti - 1
    memory[offset + 2: offset + 4] = bytes((83, 0))
    return val

def test(x):
    Return(x + 1)
    print('here')
