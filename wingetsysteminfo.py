from ctypes import windll, Structure, Union, POINTER, c_int, c_void_p, c_short, byref

class DUMMYSTRUCTNAME(Structure):
    _pack_ = 1
    _fields_ = (
        ('wProcessorArchitecture', c_short),
        ('wReserved', c_short)
    )

class DUMMYUNIONNAME(Union):
    _fields_ = (
        ('dwOemId', c_int),
        ('DUMMYSTRUCTNAME', DUMMYSTRUCTNAME)
    )

class _SYSTEM_INFO(Structure):
    _pack_ = 1
    _fields_ = (
        ('DUMMYUNIONNAME', DUMMYUNIONNAME),
        ('dwPageSize', c_int),
        ('lpMinimumApplicationAddress', c_void_p),
        ('lpMaximumApplicationAddress', c_void_p),
        ('dwActiveProcessorMask', POINTER(c_int)),
        ('dwNumberOfProcessors', c_int),
        ('dwProcessorType', c_int),
        ('dwAllocationGranularity', c_int),
        ('wProcessorLevel', c_short),
        ('wProcessorRevision', c_short)
    )

_getsysteminfo = windll.kernel32.GetSystemInfo
_getsysteminfo.argtypes = [POINTER(_SYSTEM_INFO)]

def getsysteminfo():
    systeminfo = _SYSTEM_INFO()
    _getsysteminfo(byref(systeminfo))
    return systeminfo