from ctypes import py_object, sizeof
import builtins, sys, random

def maybe():
    g = sys._getframe(1).f_globals
    if 'Maybe' in g:
        del g['Maybe']
    tp_base = py_object.from_address(id(g) + sizeof(py_object))
    class maybe_dict(dict):
        __slots__ = ()
        def __getitem__(self, key, tp_base=tp_base, dict=dict):
            try:
                tp_base.value = dict
                if key in self or key in vars(builtins):
                    return self.get(key, vars(builtins).get(key))
                elif key == 'Maybe':
                    return random.random() < 0.5
                else:
                    raise NameError(f'name {key!r} is not defined')
            finally:
                tp_base.value = __class__

        def __setitem__(self, key, value, tp_base=tp_base, dict=dict):
            try:
                tp_base.value = dict
                if key != 'Maybe':
                    return self.update({key:value})
                else:
                    raise SyntaxError('cannot assign to Maybe')
            finally:
                tp_base.value = __class__
    tp_base.value = maybe_dict
