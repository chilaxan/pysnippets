import sys, dis
from types import FunctionType
from functools import partial
from fishhook import hook

@hook.cls(FunctionType)
class func_hooks:
    def with_args(self, *args, **kwargs):
        return partial(self, *args, **kwargs)
    
    def __getattr__(self, attr):
        return self, attr

@hook(partial)
def __getattr__(self, attr):
    return self, attr

def get_dest(frame, lbl):
    instructions = [*dis.get_instructions(frame.f_code)]
    for idx, i1 in enumerate(instructions):
        if i1.opname in ['LOAD_NAME', 'LOAD_GLOBAL'] and i1.argval == 'label':
            i2 = instructions[idx + 1]
            if i2.opname == 'LOAD_ATTR' and i2.argval == lbl:
                if i1.starts_line is not None:
                    return i1.starts_line
                else:
                    print(f'Warning: label .{lbl} cannot be jumped to')
                    break
    else:
        print(f'Warning: label .{lbl} not found')

def jump(code, lbl, frame=None):
    def jumper(frame, event, arg):
        if event == 'line' and frame.f_code == code:
            dest = get_dest(frame, lbl)
            dest = odest = dest if dest is not None else frame.f_lineno
            haserr = True
            while haserr:                   
                try:
                    frame.f_lineno = dest
                    haserr = False
                except ValueError as err:
                    dest -= 1
            if odest != dest:
                # we had to change destinations to satisfy stack level, try again on next frame
                # we don't return a trace function to get to next frame faster
                jump(code, lbl)
            else:
                sys.settrace(global_trace)
                return global_trace
        return jumper
    if frame:
        frame.f_trace = jumper
    sys.settrace(jumper)

class GotoFunctionProxy:
    def __init__(self, func):
        self.func = func
        self.args = ()
        self.kwargs = {}

    def with_args(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def __getattr__(self, attr):
        jump(self.func.__code__, attr)
        return self.func(*self.args, **self.kwargs)

class Goto:
    def __getattr__(self, key):
        if isinstance(key, tuple):
            func, lbl = key
            if isinstance(func, partial):
                unbound = func.func
            else:
                unbound = func
            jump(unbound.__code__, lbl)
            return func()
        f_back = sys._getframe(1)
        target_function = f_back.f_locals.get(key) or f_back.f_globals.get(key)
        if isinstance(target_function, FunctionType):
            return GotoFunctionProxy(target_function)
        else:
            jump(f_back.f_code, key, frame=f_back)
    __mul__ = __getattr__

class Label:
    def __getattr__(*unused):
        pass

def global_trace(*unused):
    return global_trace

goto = Goto()
label = Label()
sys.settrace(global_trace)

if __name__ == '__main__':
    print('| Test Normal Jumps')
    x = 0
    label .start
    print(x)
    if x == 10:
        goto .end
    x += 1
    goto .start
    label .end
    print('| End Test Normal Jumps')

    print('| Test Function Jumps')
    def foo(var=1):
        label .A
        print('A', locals())
        goto .end
        label .B
        print('B', locals())
        label .end

    print('> goto .foo.A')
    goto .foo.A
    print('> goto .foo.B')
    goto .foo.B
    print('> goto .foo.with_args(var=2).B')
    goto .foo.with_args(var=2).B

    print('> goto *foo.with_args(var=3).A')
    goto *foo.with_args(var=3).A
    print('End Test Function Jumps')

    print('| Test Complex Jumps')
    from contextlib import contextmanager

    @contextmanager
    def mycontext(arg):
        print('entering', arg)
        yield
        print('exiting', arg)

    print('> Jump into nested Context Manager')
    goto .jmp_into_ctx
    with mycontext('ctx A'):
        print('skipped A')
        with mycontext('ctx B'):
            print('skipped B')
            label .jmp_into_ctx
            print('here')

    print('> Jump into For Loop')
    goto .jmp_into_loop
    for i in range(2):
        print('this does not run the first time')
        label .jmp_into_loop
        print(i)

    print('> Jump out of Context Manager')
    with mycontext('ctx A'):
        print('in A')
        goto .out_of_A # skip mycontext.__exit__

    label .out_of_A
    print('| End Test Complex Jumps')