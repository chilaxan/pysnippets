try:
    from native_ctypes import getmem
except:
    from ctypes import c_char
    def getmem(addr, size):
        return memoryview((c_char*size).from_address(addr)).cast('B')

__all__ = ['goto', 'label']

'''
An implementation of `goto` in pure python
'''

def getframe(depth=0):
    try:raise
    except Exception as e:
        frame = e.__traceback__.tb_frame
        for _ in range(depth + 1):
            frame = frame.f_back
        return frame

def code_map(co_code):
    idx = 0
    mapping = {}
    while co_code:
        op, arg, co_code = co_code[:2], co_code[2:]
        if op == 0x90:pass

def parse_opargs(code):
    extended_arg = 0
    for i in range(0, len(code), 2):
        op = code[i]
        arg = code[i+1] | extended_arg
        extended_arg = (arg << 8) if op == 0x90 else 0
        if op != 0x90:
            yield (i, op, arg)

import dis

def get_dest(frame, label):
    code, names = frame.f_code.co_code, frame.f_code.co_names
    frame_var = {**frame.f_globals, **frame.f_locals}.get
    last_arg = None
    for idx, op, arg in parse_opargs(code):
        if op == 106 and names[arg] == label and \
           isinstance(frame_var(names[last_arg]), Label):
                return idx - 1
        last_arg = arg
    raise RuntimeError(f'label {label!r} not found')

def patch_instr(code, idx, size, data):
    code_addr = id(code) + bytes.__basicsize__ - 1
    mem = getmem(code_addr + idx, size)
    old = mem.tobytes()
    mem[:] = data
    return old

to_fix = [None, None, None] # idx, size, data

class Goto:
    def __getattr__(self, label):
        code = (frame := getframe(1)).f_code.co_code
        idx = frame.f_lasti + 2
        dest = get_dest(frame, label)
        inj = bytes((0x72, dest & 0xff))
        dest >>= 8
        while dest > 0:
            inj = bytes((0x90, dest & 0xff)) + inj
            dest >>= 8
        old = patch_instr(code, idx, len(inj), inj)
        to_fix[:] = idx, len(old), old
    __mul__ = __getattr__

class Label:
    def __getattr__(self, name):
        if None not in to_fix:
            frame = getframe(1)
            patch_instr(frame.f_code.co_code, *to_fix)
            to_fix[:] = None, None, None

goto = Goto()
label = Label()

x = 0
label .start
print(x)
if x == 10:
    goto .end
x += 1
goto .start
label .end

f = lambda:int(i) if label .start or (i:=input('type a number: ')).isnumeric() else goto .start

def computedgoto():
    i = 0
    dest = 'start'
    label. start
    print(i)
    if i == 10:
        dest = 'end'
    i += 1
    goto *dest
    label. end
