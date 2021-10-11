import inspect
import types
def conv_args(func):
    code = func.__code__
    flags = code.co_flags
    argcount = code.co_argcount
    converters = []
    kwarg_conv = None
    arg_conv = None
    for name, param in inspect.signature(func).parameters.items():
        if param.annotation is not param.empty:
            conv = param.annotation
        else:
            conv = lambda a:a
        if not param.kind & (param.VAR_KEYWORD | param.VAR_POSITIONAL):
            converters.append(conv)
        elif param.kind & param.VAR_KEYWORD:
            flags -= flags & 0x8
            argcount += 1
            kwarg_conv = conv
        elif param.kind & param.VAR_POSITIONAL:
            flags -= flags & 0x4
            argcount += 1
            arg_conv = conv
    func.__code__ = code.replace(
        co_flags = flags,
        co_argcount = argcount,
    )
    def wrapper(*args, **kwargs):
        return func(
            *(conv(arg) for conv, arg in zip(converters, args[:code.co_argcount])),
            *() if arg_conv is None else [arg_conv(args[code.co_argcount:])],
            *() if kwarg_conv is None else [kwarg_conv(kwargs)]
        )
    return wrapper

def verify(typ):
    def wrapper(arg):
        if typ is None:
            return arg
        if hasattr(typ, '__args__') and hasattr(typ, '__origin__'):
            assert isinstance(arg, typ.__origin__), f'{arg!r} is not an instance of {typ!r}'
            if issubclass(typ.__origin__, dict):
                assert len(typ.__args__) == 2, 'invalid subscript for dictionary'
                ktyp, vtyp = typ.__args__
                for k, v in arg.items():
                    verify(ktyp)(k)
                    verify(vtyp)(v)
            else:
                assert len(typ.__args__) == 1, 'invalid subscript for array'
                vtyp, = typ.__args__
                for v in arg:
                    verify(typ.__args__)(v)
        else:
            assert isinstance(arg, typ), f'{arg!r} is not an instance of {typ!r}'
        return arg
    return wrapper

@conv_args
def sum_l(a: verify(list[int])):
    return sum(a)

@conv_args
def foo(a: verify(int | str)):
    print(a)

from dataclasses import dataclass

@dataclass
class Foo:
    a: int = None
    b: int = None

    @classmethod
    def from_dict(cls, dct):
        return cls(**dct)

@conv_args
def foo_func(a:int, b: tuple, *args: list, **kwargs: Foo.from_dict):
    print(a, b, args, kwargs)

foo_func('1', 'string', 'a', 'b', a=1, b=2)
