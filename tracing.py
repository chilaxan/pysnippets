import sys, dis

def trace(tf):
    def wp(f):
        def inner(*a, **k):
            try:
                sys.settrace(tf)
                return f(*a, **k)
            finally:
                sys.settrace(None)
        return inner
    return wp

def jump_trace(frame, line, arg):
    frame.f_trace_opcodes = True
    if line == 'opcode':
        idx = frame.f_lasti
        op, arg = frame.f_code.co_code[idx: idx + 2]
        if dis.opname[op] in ['LOAD_GLOBAL', 'LOAD_NAME']:
            sarg = frame.f_code.co_names[arg]
            if isinstance(sarg, str) and sarg.startswith('JUMP_'):
                _, d, n = sarg.split('_')
                try:
                    mvs = {
                        'UP': frame.f_lineno - int(n),
                        'DOWN': frame.f_lineno + int(n),
                        'TO': int(n)
                    }
                    frame.f_lineno = mvs.get(d, frame.f_lineno)
                    return
                except:
                    pass
    return jump_trace

@trace(jump_trace)
def foo():
    x = 0
    print(x)
    x += 1
    if x == 10:
        return
    JUMP_UP_4
