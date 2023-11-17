from asm import COMPILER, DECOMPILER, addressof

import ctypes as CT
from mmap import *
libc = CT.cdll.LoadLibrary(None)

errno = CT.c_int.in_dll(CT.pythonapi,"errno")

def errcheck(ret, func, args):
    if ret == -1:
        e = errno.value
        raise OSError(e)
    return ret

mprotect = libc.mprotect
mprotect.argtypes = (CT.c_void_p, CT.c_size_t, CT.c_int)
mprotect.restype = CT.c_int
mprotect.errcheck = errcheck

mmap = libc.mmap
mmap.restype = CT.c_void_p
mmap.argtypes = (CT.c_void_p, CT.c_size_t,
                          CT.c_int, CT.c_int,
                          CT.c_int, CT.c_size_t)

mmap.errcheck = errcheck

munmap = libc.munmap
munmap.restype = CT.c_int
munmap.argtypes = (CT.c_void_p, CT.c_size_t)

munmap.errcheck = errcheck

def execASM(asm, *args, restype=CT.c_int, argtypes=()):
    if isinstance(asm, str):
        asm_l, _ = COMPILER.asm(asm)
        asm = bytes(asm_l)
    code_address = mmap(None, len(asm),
                             PROT_READ | PROT_EXEC,
                             MAP_PRIVATE | MAP_ANONYMOUS,
                             -1, 0)
    mprotect(code_address, len(asm), PROT_READ | PROT_WRITE)
    (CT.c_char * len(asm)).from_address(code_address)[:] = asm
    mprotect(code_address, len(asm), PROT_READ | PROT_EXEC)
    try:
        func = CT.cast(code_address, CT.CFUNCTYPE(restype, *argtypes))
        func.errcheck = errcheck
        return func(*args)
    finally:
        munmap(code_address, len(asm))

def disassemble_func(cfunc, length=0x20, offset=0):
    mem = (CT.c_char * length).from_address(addressof(cfunc) + offset)
    for (address, size, mnemonic, op_str) in DECOMPILER.disasm_lite(mem, 0x0):
    	print("0x%x:\t%s\t%s" %(address, mnemonic, op_str))

def call_function(address, *args, **kwargs):
    asm = '''
        ldr x8, .+8
        br x8
    '''
    ops, _ = COMPILER.asm(asm)
    asm = bytes(ops) + address.to_bytes(8, 'little')
    return execASM(asm, *args, **kwargs)

def call_syscall(num, *args, **kwargs):
    asm = f'''
        mov x16, #{hex(num)}
        svc #0x80
        ret
    '''
    ops, _ = COMPILER.asm(asm)
    asm = bytes(ops)
    return execASM(asm, *args, **kwargs)

PAGE_SIZE = libc.getpagesize()
MEM_READ = 1
MEM_WRITE = 2
MEM_EXEC = 4

def my_mprotect(address, size, prots):
    addr_align = address & ~(PAGE_SIZE - 1)
    mem_end = (address + size) & ~(PAGE_SIZE - 1)
    if (address + size) > mem_end:
        mem_end += PAGE_SIZE
    memlen = mem_end - addr_align
    print(hex(address))
    print(hex(memlen))
    print(hex(prots))
    return call_function(addressof(mprotect), addr_align, memlen, prots, argtypes=(CT.c_void_p, CT.c_size_t, CT.c_int))

B = bytes(range(255))
#print(my_mprotect(id(B), 5, MEM_READ))

def test_asm(target_addr, size, src_addr):
    addr_align = target_addr & ~(PAGE_SIZE - 1)
    mem_end = (target_addr + size) & ~(PAGE_SIZE - 1)
    if (target_addr + size) > mem_end:
        mem_end += PAGE_SIZE
    memlen = mem_end - addr_align
    x0 = addressof(mprotect)
    x1 = addr_align
    x2 = memlen
    x3 = PROT_READ | PROT_WRITE
    x4 = PROT_READ | PROT_EXEC
    x5 = src_addr
    x6 = size
    x7 = target_addr
    # does not work fml
    # need to save LR before BL instruction?
    # might be better to use system call directly?
    asm = '''
        mov x8, x0;
        mov x0, x1;
        mov x1, x2;
        mov x2, x3;
        bl x8;
    write_loop:
        cmp x6, xzr;
        be done;
        ldrb x3, [x5];
        strb x3, [x7];
        sub x5, x5, #1;
        sub x7, x7, #1;
        sub x6, x6, #1;
        b write_loop;
    done:
        mov x2, x4;
        bl x8;
        ret
    '''
    return execASM(
        asm,
        x0, x1, 
        x2, x3, 
        x4, x5, 
        x6, x7,
        argtypes=[CT.c_void_p] * 8)