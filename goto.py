from ctypes import c_char
def getmem(addr, size):
    return memoryview((c_char*size).from_address(addr)).cast('B')

__all__ = ['goto', 'label']

'''
An implementation of `goto` in pure python
'''

def get_dest(frame, label):
    code, names = frame.f_code.co_code, frame.f_code.co_names
    frame_var = {**frame.f_globals, **frame.f_locals}.get
    ops, args = code[::2], code[1::2]
    for idx, (op, arg) in enumerate(zip(ops, args)):
        if op == 106 and names[arg] == label and \
           isinstance(frame_var(names[args[idx - 1]]), Label):
                return (idx - 1) * (1 if int.__flags__ & (1 << 8) else 2)
    raise RuntimeError(f'label {label!r} not found')

def set_instr(code, idx, op, arg):
    code_addr = id(code) + bytes.__basicsize__ - 1
    mem = getmem(code_addr, len(code))
    (op, arg), mem[idx:idx + 2] = mem[idx:idx + 2], bytes((op, arg))
    return op, arg

restore_instr = [None, None, None]

class Goto:
    def __getattr__(self, label):
        code = (frame := sys._getframe(1)).f_code.co_code
        idx = frame.f_lasti + 2
        op, arg = set_instr(code, idx, 114, get_dest(frame, label))
        restore_instr[:3] = (idx, op, arg)
    __mul__ = __getattr__

class Label:
    def __getattr__(self, name):
        if None not in restore_instr:
            frame = sys._getframe(1)
            set_instr(frame.f_code.co_code, *restore_instr)
            restore_instr[:3] = (None, None, None)

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
