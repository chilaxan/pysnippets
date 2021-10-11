from decimal import Decimal
from asm_hook import *

class d(c_double):pass
# subclass hack to delay conversion
# ctypes type conversion seems to clobber the argument for this function
# This is likely due to this function using the xmmr registers
# (due to it recieving a double and optimization level)
# delaying conversion with a subclass fixes the issue
@hook(pythonapi.PyFloat_FromDouble, restype=py_object, argtypes=[d])
def pyfloat_fromdouble(doub):
    return Decimal(doub.value) # conversion happens here, while PyFloat_FromDouble is unpatched
    # values are likely still clobbered, but the value has already been copied from xmmr register

@hook(pythonapi.PyFloat_FromString, restype=py_object, argtypes=[py_object])
def pyfloat_fromstring(string):
    return Decimal(string)
