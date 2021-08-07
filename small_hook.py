from ctypes import *
import sys

basic_size = sizeof(c_void_p)

def generate_slotmap(slotmap={}):
    if slotmap:
        return slotmap

    class HeapTypeObj:
        __slots__ = ()

    size = type(HeapTypeObj).__sizeof__(HeapTypeObj)
    static_size = type.__sizeof__(type)
    cls_mem = (c_char*size).from_address(id(HeapTypeObj))
    address = id(HeapTypeObj)
    pointers = [(offset, ptr) for offset, ptr in enumerate(memoryview(cls_mem.raw).cast('l'))
                    if address < ptr < address + len(cls_mem)]

    sizes = []
    last_addr = None
    for offset, ptr in sorted(pointers, key=lambda i:i[1]):
        if last_addr is not None:
            sizes.append(ptr - last_addr)
        last_addr = ptr

    sizes.append(last_addr - address + len(cls_mem))

    structs = [(0, static_size)] \
            + [(offset, size) for (offset, _), size in zip(pointers, sizes)]

    seen = set()
    wrappers = set()

    for subcls in object.__subclasses__():
        for name, method in vars(subcls).items():
            if not name.startswith('__') or not callable(method) or name in seen:
                continue
            seen.add(name)
            oldmem = cls_mem.raw
            try:
                setattr(HeapTypeObj, name, None)
            except (TypeError, AttributeError) as e:
                continue
            if oldmem[basic_size:] != cls_mem.raw[basic_size:]:
                for i in range(0, len(oldmem), basic_size):
                    ovalue = int.from_bytes(oldmem[i:i + basic_size], sys.byteorder)
                    nvalue = int.from_bytes(cls_mem.raw[i:i + basic_size], sys.byteorder)
                    if ovalue != nvalue and i != 0:
                        wrappers.add((
                            i,
                            name,
                            nvalue
                        ))
                delattr(HeapTypeObj, name)
