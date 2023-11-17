from fishhook import hook

class compose:
    def __init__(self, f1, f2):
        self.f1 = f1
        self.f2 = f2

    def __call__(self, *args, **kwargs):
        return self.f2(self.f1(*args, **kwargs))

    def append(self, func):
        return self @ func

    def prepend(self, func):
        return func @ self

    def __repr__(self):
        f1 = self.f1.__name__ if hasattr(self.f1, "__name__") else self.f1
        f2 = self.f2.__name__ if hasattr(self.f2, "__name__") else self.f2
        return f'({f1} @ {f2})'

class bind:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return self.func(*self.args, *args, **self.kwargs, **kwargs)

    def __repr__(self):
        fn = self.func.__name__ if hasattr(self.func, "__name__") else self.func
        args = ", ".join(map(repr, self.args))
        kwargs = ", ".join(f"{key} = {val!r}" for key, val in self.kwargs.items())
        return f'bind({fn}{", " if args or kwargs else ""}{args + ", " if kwargs else args}{kwargs})'

d = lambda f:f

@d(lambda f:[hook(c, func=f) for c in object.__subclasses__() if vars(c).get('__call__')] or f)
def __matmul__(self, other):
    return compose(self, other)
