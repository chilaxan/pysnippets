from ctypes import *
import sys
import dis

pythonapi.Py_IncRef.argtypes=[py_object]

class Singleton(type):
    def __new__(self, name, bases, body):
        frame = sys._getframe(1)
        segment = frame.f_code.co_code[frame.f_lasti + 2:]
        num_decos = 0
        for op, arg in zip(segment[::2], segment[1::2]):
            if op == dis.opmap['CALL_FUNCTION'] and arg == 1:
                num_decos += 1
            else:
                break
        stacktop = POINTER(py_object).from_address(id(frame) + sizeof(c_void_p) * 8)
        args = stacktop[:num_decos]
        for idx in range(num_decos):
            f = lambda c:c
            pythonapi.Py_IncRef(f)
            stacktop[idx] = f
        cls = super().__new__(self.__base__, name, bases, body)
        return cls(*args)

@1
@2
@(1,2,3)
class instance(metaclass=Singleton):
    def __init__(self, *initial_values):
        print('instance initialized with', *initial_values)
        self.args = initial_values

    def __repr__(self):
        return f'instance{self.args}'

print(instance)
