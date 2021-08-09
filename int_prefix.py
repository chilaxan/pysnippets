import sys
import fishhook
import f_locals
import dis
from ctypes import (
    c_byte,
    py_object,
    c_void_p,
    POINTER,
    sizeof
)

handlers = {}

register = lambda op:lambda f:handlers.update({op:f}) or f

@register(dis.opmap['LOAD_NAME'])
@register(dis.opmap['LOAD_GLOBAL'])
def handle_name(frame, arg, num):
    name = frame.f_code.co_names[arg]
    frame.f_globals[name] = num

@register(dis.opmap['LOAD_FAST'])
def handle_fast(frame, arg, num):
    name = frame.f_code.co_varnames[arg]
    frame.f_locals[name] = num

# may implement for more containers later

def unary_hook(self, frame):
    code = frame.f_code
    co_code = code.co_code
    unary_op = co_code[frame.f_lasti]
    load_op, load_arg = co_code[frame.f_lasti - 2: frame.f_lasti]
    inc = 0
    for idx in range(frame.f_lasti, len(co_code), 2):
        if co_code[idx] == unary_op:
            inc += 1
        else:
            break
    if unary_op == dis.opmap['UNARY_NEGATIVE']:
        self -= inc // 2
    else:
        self += inc // 2
    if func := handlers.get(load_op):
        func(frame, load_arg, self)
    address = id(co_code) + bytes.__basicsize__ - 1 + frame.f_lasti
    for i in range(inc):
        c_byte.from_address(address + (i * 2)).value = dis.opmap['NOP']
    def tfunc(*args, co_code=co_code):
        if tfunc.n == 2:
            for i in range(inc):
                c_byte.from_address(address + (i * 2)).value = unary_op
            sys.setprofile(None)
        else:
            tfunc.n += 1
    tfunc.n = 0
    sys.setprofile(tfunc)
    if inc % 2 == 0:
        return self
    else:
        if unary_op == dis.opmap['UNARY_NEGATIVE']:
            return ~self + 1
        else:
            if self < 0:
                return ~self + 1
        return self

@fishhook.hook_cls(int)
class int_hooks:
    def __pos__(self):
        return unary_hook(self, sys._getframe(1))

    def __neg__(self):
        return unary_hook(self, sys._getframe(1))
