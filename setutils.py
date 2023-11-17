import itertools
import fishhook

@fishhook.hook(set)
def __mul__(self, other):
    return itertools.product(self, other)

@fishhook.hook(itertools.product)
def __mul__(self, other):
    cls, args = self.__reduce__()
    return cls(*args, other)
