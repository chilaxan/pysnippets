import sys, dis

queue = {}

class Evil:
    def __eq__(self, other):
        return other

def getclsdict(cls):
    return cls.__dict__ == Evil()

def object_enter(self, *args):
    frame = sys._getframe(1)
    lasti = frame.f_lasti
    f_code = frame.f_code
    co_code = f_code.co_code
    if co_code[lasti + 2] == dis.opmap['STORE_NAME']:
        name = f_code.co_names[co_code[lasti + 3]]
        queue[name] = self
    return self

def object_exit(self, *args):
    frame = sys._getframe(1)
    loc = frame.f_locals
    for name, value in queue.copy().items():
        if value is self and name in loc and loc[name] is self:
            del loc[name]
            del queue[name]


obj_dct = getclsdict(object)
obj_dct['__enter__'] = object_enter
obj_dct['__exit__'] = object_exit
