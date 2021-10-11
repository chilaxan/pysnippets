import dis

def decompile(byc):
    jmp_tbl = {}
    decomp = []
    idx = 0
    while idx < len(byc):
        op, arg = byc[idx: idx + 2]
        idx += 2
        while dis.opname[op] == 'EXTENDED_ARG':
            oarg = arg
            op, arg = byc[idx: idx + 2]
            arg |= oarg << 8
            idx += 2
        decomp.append([dis.opname[op], arg])
    for idx, ((op, arg), lst) in enumerate(zip(decomp, decomp)):
        if op == 'JUMP_FORWARD':
            jmp_tbl[id(lst)] = decomp[idx + (arg // 2) + 1]
        elif 'JUMP' in op:
            jmp_tbl[id(lst)] = decomp[arg // 2]
    return decomp, jmp_tbl

def insert_extensions(decomp):
    while any(filter(lambda t:t[1] > 255, decomp)):
        for idx, (op, arg) in enumerate(decomp[:]):
            nshift = (arg.bit_length() / 8).__ceil__()
            if op != 'JUMP_FORWARD' and 'JUMP' in op and nshift:
                arg += (nshift - 1) * 2
            if arg > 255:
                decomp[idx][1] = arg & 255
                decomp.insert(idx, ['EXTENDED_ARG', arg >> 8])
                break

def find(decomp, dest):
    for idx, lst in enumerate(decomp):
        if lst is dest:
            return idx

def recompile(decomp, jmp_tbl):
    insert_extensions(decomp) # insert EXTENDED_ARG for non JUMPs
    for idx, ((op, arg), lst) in enumerate(zip(decomp, decomp)):
        if 'JUMP' in op:
            offset = (idx + 1) if op == 'JUMP_FORWARD' else 0
            dest_op = jmp_tbl.get(id(lst))
            if (dest := find(decomp, dest_op)) is not None:
                arg = lst[1] = (dest - offset) * 2
    insert_extensions(decomp) # insert EXTENDED_ARG for JUMPs
    return b''.join(bytes([dis.opmap[op], arg]) for op, arg in decomp)

def compute_stack_effect(decomp, jmp_tbl, end, start):
    SE = 0
    idx = 0
    segment = decomp[start + 1: end]
    while idx < len(segment):
        (op, arg) = lst = segment[idx]
        isjump = 'JUMP' in op
        SE += dis.stack_effect(
            dis.opmap[op],
            arg if dis.opmap[op] > dis.HAVE_ARGUMENT else None,
            jump = isjump
        )
        if isjump:
            idx = find(segment, jmp_tbl[id(lst)])
        else:
            idx += 1
    return SE

def get_name(code, op, arg):
    names = {
        'LOAD_FAST': code.co_varnames,
        'LOAD_NAME': code.co_names,
        'LOAD_GLOBAL': code.co_names,
        'LOAD_DEREF': code.co_freevars,
    }.get(op)
    if names is None:
        return
    return names[arg]

def find_tco_segment(code, decomp, jmp_tbl):
    for idx, (op, arg) in enumerate(decomp):
        if op != 'CALL_FUNCTION' or decomp[idx + 1] != ['RETURN_VALUE', 0]:
            continue
        for b in range(idx + 1):
            bop, barg = decomp[idx - b]
            if get_name(code, bop, barg) == code.co_name and \
               arg == compute_stack_effect(decomp, jmp_tbl, idx, idx - b):
                return arg, b, idx

def single_pass_tco(code):
    decomp, jmp_tbl = decompile(code.co_code)
    if segment := find_tco_segment(code, decomp, jmp_tbl):
        arg_count, start, end = segment
        decomp[end - start][:] = ['NOP', 0]
        decomp[end][:] = ['JUMP_ABSOLUTE', 0]
        jmp_tbl[id(decomp[end])] = decomp[0]
        del decomp[end + 1]
        for i in range(arg_count):
            decomp.insert(end, ['STORE_FAST', i])
    return code.replace(co_code=recompile(decomp, jmp_tbl))

def tco(func):
    code = func.__orig_code__ = func.__code__
    while code != (code := single_pass_tco(code)):
        pass
    func.__code__ = code
    return func

#*-- TESTING --*#

@tco
def fact(n, acc=1):
    if (n < 2):
        return acc
    return fact(n - 1, n * acc)

dis.dis(fact)

def fib(n=1000, a=0, b=1):
    if n == 0:
        return a
    if n == 1:
        return b
    return fib(n - 1, b, a + b);

import timeit
import sys
sys.setrecursionlimit(2000)
print(timeit.timeit(fib, number=10000))
print(timeit.timeit(tco(fib), number=10000))
