def sizeof(obj):
    return type(obj).__sizeof__(obj)

TUPLE_HEADER = sizeof(())
BYTES_HEADER = sizeof(b'') - 1
PTR_SIZE = sizeof((0,)) - TUPLE_HEADER
MAX_INT =  (1 << PTR_SIZE * 8 - 1) - 1
ENDIAN = ['little','big'][1%memoryview(b'\1\0').cast('h')[0]]

def load_addr(addr):
    capsule = []
    class magic_class:
        __slots__ = ('obj',)
        def __repr__(self):
            capsule.append(self.obj)
    magic = lambda:None
    b_mem = b''.join(n.to_bytes(PTR_SIZE, ENDIAN) for n in (
        1,
        id(magic_class),
        addr
    ))
    b_addr = (id(b_mem) + BYTES_HEADER).to_bytes(PTR_SIZE, ENDIAN)
    offset = id(b_addr) + BYTES_HEADER
    offset -= id(magic.__code__.co_names) + TUPLE_HEADER
    offset //= PTR_SIZE
    if offset < 0:
        offset += 0xffffffff + 1
    co_code = bytes((0x65, offset & 0xff, 0x53, 0))
    offset >>= 8
    while offset > 0:
        co_code = bytes((0x90, offset & 0xff)) + co_code
        offset >>= 8
    magic.__code__ = magic.__code__.replace(
        co_code=co_code
    )
    try:
        magic()
    except SystemError as e:
        return capsule.pop()

#def make_getmem():
#    memory_backing = b''.join(n.to_bytes(PTR_SIZE, ENDIAN) for n in (
#        1,
#        id(bytearray),
#        MAX_INT,
#        0, 0, 0, 0
#    ))
#
#    memory = memoryview(load_addr(id(memory_backing) + BYTES_HEADER))
#
#    def getmem(start, size, _=memory_backing):
#        return memory[start:start + size]
#    return getmem
#
#getmem = make_getmem()
