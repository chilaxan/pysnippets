from ctypes import py_object, c_char
import atexit, builtins, sys, dis

'''
Allows for running an aribitrary function when a name is not found dynamically
'''

def init_missing_hook(dct, func):
    ob_base_p = py_object.from_address(id(dct) + 8)
    class missing_hook(dict):
        __slots__ = ()
        def __missing__(self, key, ob_base_p=ob_base_p, builtins=builtins):
            try:
                ob_base_p.value = builtins.dict
                return (builtins.__dict__ | self)[key]
            except KeyError:
                return func(self, key)
            finally:
                ob_base_p.value = __class__

    ob_base_p.value = missing_hook

    @atexit.register
    def unhook():
        ob_base_p.value = dict
    return unhook

def builtinexc(exc, depth=1):
    frame = sys._getframe(1 + depth)
    addr = id(frame.f_code.co_code) + bytes.__basicsize__ - 1
    mem = (c_char * len(frame.f_code.co_code)).from_address(addr)
    mem[frame.f_lasti + 2:frame.f_lasti + 4] = bytes([dis.opmap['RAISE_VARARGS'], 1])
    return exc

# modified from https://ao.gl/how-to-convert-numeric-words-into-numbers-using-python/
def parse_int(dct, textnum, numwords={}):
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]
      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
      scales = ["hundred", "thousand", "million", "billion", "trillion"]
      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.replace("_"," ").split():
        if word not in numwords:
          return builtinexc(NameError(f"name {textnum!r} is not defined"), 3)
        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0
    return result + current

def lexical_literals():
    '''
    allows for english numbers to be expressed by words dynamically
    ie:
        one -> 1
        one_hundred_and_seven -> 107
    '''
    init_missing_hook(sys._getframe(1).f_globals, parse_int)

def advanced_name_error(dct, name):
    for mapping in [sys._getframe(2).f_locals, dct]:
        for key in mapping:
            if name.lower() == key.lower():
                return builtinexc(NameError(f'name {name!r} is not defined, did you mean {key!r}'), 2)
    if name in sys.modules:
        return builtinexc(NameError(f'module {name!r} is not imported here'), 2)
    for modname, mod in sys.modules.items():
        if getattr(mod, name, None):
            return builtinexc(NameError(f'name {name!r} is not defined here, but is defined in module {modname!r}'), 2)
    return builtinexc(NameError(f'name {name!r} is not defined'), 2)

def better_name_errors():
    '''
    provides some slightly more user friendly Name errors
    '''
    init_missing_hook(sys._getframe(1).f_globals, advanced_name_error)

import warnings, importlib.util
def auto_import(dct, name):
    if importlib.util.find_spec(name):
        warnings.warn(f'implicitly importing module {name!r}', RuntimeWarning, 3)
        mod = __import__(name)
        dct[name] = mod
        return mod
    else:
        return builtinexc(NameError(f'name {name!r} is not defined'), 2)

def implicit_imports():
    '''
    implicitly import modules
    '''
    init_missing_hook(sys._getframe(1).f_globals, auto_import)
