from ctypes import *
import dis

BASE_SIZE = sizeof(c_void_p)
BYTES_OFFSET = b''.__sizeof__() - 1

def getframe(depth=0):
    try:raise
    except Exception as e:
        frame = e.__traceback__.tb_frame
        for _ in range(depth + 1):
            frame = frame.f_back
        return frame

def inject_call(frame, inj_idx=0, argc=0):
    co_code = frame.f_code.co_code
    instructions = (c_char * 4).from_address(id(co_code) + BYTES_OFFSET + frame.f_lasti + inj_idx)
    orig = instructions.raw
    instructions[:] = bytes([
        dis.opmap['CALL_FUNCTION'], argc,
        dis.opmap['JUMP_ABSOLUTE'], frame.f_lasti + inj_idx
    ])
    def cleanup():
        instructions[:] = orig
    return cleanup

def make_stc():
    capsule = {}
    @CFUNCTYPE(py_object, py_object)
    def call(self):
        tptr = capsule.pop('tptr')
        oval = capsule.pop('oval')
        clean = capsule.pop('clean')
        retv = capsule.pop('retv')
        tptr.value = oval
        clean()
        return retv

    call_addr = cast(call, c_void_p).value

    def setup_tp_call(typ, ret, cleanup):
        tpcall_pointer = c_void_p.from_address(id(typ) + 16 * BASE_SIZE)
        oval = tpcall_pointer.value
        tpcall_pointer.value = call_addr
        capsule.update(tptr=tpcall_pointer, oval=oval, retv=ret, clean=cleanup)
    return setup_tp_call

setup_tp_call = make_stc()

def custom_contains(func):
    def wrapper(self, other):
        frame = getframe(1)
        oparg = frame.f_code.co_code[frame.f_lasti + 1]
        ret = func(self, other, oparg)
        cleanup = inject_call(frame)
        setup_tp_call(bool, ret, cleanup)
    return wrapper

class Foo:
    @custom_contains
    def __contains__(self, item, flag):
        return self, item, flag
