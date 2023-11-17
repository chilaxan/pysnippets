import platform
import sys
import os
import capstone as CS
import keystone as KS
import ctypes as CT

libc = CT.cdll.LoadLibrary(None)
ENDIAN = 'LITTLE' if memoryview(b'\1\0').cast('h')[0]==1 else 'BIG'
BIT_SIZE = sys.maxsize.bit_length() + 1
ARCH = platform.machine().upper()
if ARCH == 'AMD64' or 'X86' in ARCH:
    ARCH = 'X86'

if ARCH == 'AARCH64':
    ARCH = 'ARM64'

assert ARCH in ['ARM64', 'X86'], f'Unsupported/Untested Architecture: {ARCH}'

formats = {
    'ARM64': 'b #{offset}',
    'X86': 'jmp [{offset}]'
}

def addressof(cfunc):
    ptr = CT.c_void_p.from_address(CT.addressof(cfunc))
    return ptr.value

def maketools():
    cs_arch = getattr(CS, f'CS_ARCH_{ARCH}')
    cs_mode = getattr(CS, f'CS_MODE_{ENDIAN}_ENDIAN')
    ks_arch = getattr(KS, f'KS_ARCH_{ARCH}')
    ks_mode = getattr(KS, f'KS_MODE_{ENDIAN}_ENDIAN')
    if ARCH == 'X86':
        cs_mode += getattr(CS, f'CS_MODE_{BIT_SIZE}')
        ks_mode += getattr(KS, f'KS_MODE_{BIT_SIZE}')

    return CS.Cs(cs_arch, cs_mode), KS.Ks(ks_arch, ks_mode), formats[ARCH]

DECOMPILER, COMPILER, JMP_ASM = maketools()

def getmem(addr, size):
    return (CT.c_char * size).from_address(addr)

errno = CT.c_int.in_dll(CT.pythonapi,"errno")

def errcheck(ret, func, args):
    if ret == -1:
        e = errno.value
        raise OSError(e)
    return ret

def build_writeASM():
    if os.name == 'nt':
        PAGE_EXECUTE_READ = 0x20
        PAGE_READWRITE = 0x04
        VirtualProtect = CT.windll.kernel32.VirtualProtect
        VirtualProtect.argtypes = [CT.c_void_p, CT.c_size_t, CT.c_int, CT.POINTER(CT.c_int)]
        def writeASM(address, asm):
            mem = getmem(address, len(asm))
            old = CT.c_int(1)
            VirtualProtect(address, len(asm), PAGE_READWRITE, CT.pointer(old))
            try:
                return mem.raw
            finally:
                mem[:] = asm
                VirtualProtect(address, len(asm), PAGE_EXECUTE_READ, CT.pointer(old))

    else:
        PAGE_SIZE = libc.getpagesize()
        MEM_READ = 1
        MEM_WRITE = 2
        MEM_EXEC = 4

        libc.mprotect.argtypes = (CT.c_void_p, CT.c_size_t, CT.c_int)
        libc.mprotect.restype = CT.c_int
        libc.mprotect.errcheck = errcheck

        def writeASM(address, asm):
            mem = getmem(address, len(asm))
            addr_align = address & ~(PAGE_SIZE - 1)
            mem_end = (address + len(asm)) & ~(PAGE_SIZE - 1)
            if (address + len(asm)) > mem_end:
                mem_end += PAGE_SIZE
            memlen = mem_end - addr_align
            try:
                return mem.raw
            finally:
                libc.mprotect(addr_align, memlen, MEM_READ | MEM_WRITE)
                mem[:] = asm
                libc.mprotect(addr_align, memlen, MEM_READ | MEM_EXEC)

    return writeASM

writeASM = build_writeASM()

def hook(cfunc, restype=CT.c_int, argtypes=()):
    cfunctype = CT.PYFUNCTYPE(restype, *argtypes)
    cfunc.restype, cfunc.argtypes = restype, argtypes
    o_ptr = addressof(cfunc)
    def wrapper(func):
        @cfunctype
        def injected(*args, **kwargs):
            try:
                writeASM(o_ptr, default)
                return func(*args, **kwargs)
            finally:
                writeASM(o_ptr, jmp)
        n_ptr = addressof(injected)
        jmp_b, _ = COMPILER.asm(JMP_ASM.format(offset=hex(n_ptr - o_ptr)))
        jmp = bytes(jmp_b)
        default = writeASM(o_ptr, jmp)
        def unhook():
            writeASM(o_ptr, default)
        injected.unhook = unhook
        return injected
    return wrapper

input()
#@hook(CT.pythonapi.PyDict_SetDefault, restype=CT.py_object, argtypes=[CT.py_object, CT.py_object, CT.py_object])
#def setdefault(self, key, value):
#    if key == 'MAGICVAL':
#        return self
#    
#    return CT.pythonapi.PyDict_SetDefault(self, key, value)

#CT.pythonapi.PyUnicode_InternFromString.restype = CT.py_object
#interned = CT.pythonapi.PyUnicode_InternFromString(b'MAGICVAL')
#setdefault.unhook()
#print(interned)