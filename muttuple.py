import gc
from fishhook import hook_cls
from ctypes import py_object, pythonapi, sizeof

base_size = sizeof(py_object)

'''
Makes tuples mutable
'''

def replace_tuple(self, new):
    for container in gc.get_referrers(self):
        if isinstance(container, dict):
            for k, v in container.items():
                if v is self:
                    container[k] = new
        elif isinstance(container, list):
            for i, v in enumerate(container):
                if v is self:
                    container[i] = new
        elif isinstance(container, tuple):
            for i, v in enumerate(container):
                if v is self:
                    temp = list(container)
                    temp[i] = new
                    replace_tuple(container, tuple(temp))
        elif isinstance(container, set):
            container.remove(self)
            container.add(new)

def patch_exc(ex):
    ex.args = *map(
        str.replace,
        ex.args,
        ['list'] * len(ex.args),
        ['tuple'] * len(ex.args)
    ),
    return ex

@hook_cls(tuple)
class tuple_patch:
    def __setitem__(self, idx, value):
        temp = list(self)
        try:
            temp[idx]
        except Exception as ex:
            raise patch_exc(ex)
        if isinstance(idx, int):
            pythonapi.Py_IncRef(py_object(value))
            ptr = py_object.from_address(id(self) + (3 + idx) * base_size)
            orig_obj, ptr.value = ptr.value, value
            pythonapi.Py_DecRef(py_object(orig_obj))
        else:
            temp[idx] = value
            replace_tuple(self, tuple(temp))

    def __delitem__(self, idx):
        temp = list(self)
        try:
            del temp[idx]
        except Exception as ex:
            raise patch_exc(ex)
        replace_tuple(self, tuple(temp))

    for method in dir([]):
        if not ((method.startswith('__') and method.endswith('__')) or method in dir(())):
            def func(self, *args, n=method, **kwargs):
                temp = list(self)
                try:
                    ret = getattr(temp, n)(*args, **kwargs)
                except Exception as ex:
                    raise patch_exc(ex)
                replace_tuple(self, tuple(temp))
                return ret
            func.__name__ = method
            func.__qualname__ = method
            locals()[method] = func
    del method, func
