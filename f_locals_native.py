def make_locals():
    import sys
    to_update = {}
    def locals():
        frame = sys._getframe(1)
        return to_update.setdefault(frame, {**frame.f_locals})

    def tracefunc(frame, what, arg):
        if frame in to_update:
            for key in frame.f_locals.copy():
                if key not in to_update[frame]:
                    del frame.f_locals[key]
            for key, val in to_update[frame].items():
                if key not in frame.f_locals or frame.f_locals[key] != val:
                    frame.f_locals[key] = val
            del to_update[frame]
        return tracefunc
    sys.settrace(tracefunc)
    return locals

(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)['locals'] = make_locals()

def test_reassign():
    abc = 'Old Value'
    print(abc) # 'Old Value'
    locals()['abc'] = 'New Value'
    print(abc) # 'New Value'

def test_preassign():
    locals()['abc'] = 'New Value'
    print(abc)
    abc = None # forces abc to be a local

def test_dellocal():
    abc = 'Old Value'
    del locals()['abc']
    print(abc)