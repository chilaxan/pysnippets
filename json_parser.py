def check(src, chars, msg):
    assert src, msg
    next = src.pop()
    assert next in chars, msg
    return next

def read_str(src):
    ret = ''
    check(src, '"', 'Missing String Initializer')
    while src and src[-1] != '"':
        next = src.pop()
        if next == '\\':
            spec = check(src, r'\"bfnrtu', 'Invalid Escape Specifier')
            if spec == 'u':
                assert len(src) >= 4, 'Not Enough Characters Following \\u'
                codepoint = ''.join(src.pop() for _ in range(4))
                assert all(c in '0123456789abcdefABCDEF' for c in codepoint), 'Invalid Codepoint'
                ret += chr(int(codepoint, 16))
            else:
                ret += ('\b\f\n\r\t'+spec)[('bfnrt'+spec).index(spec)]
        else:
            ret += next
    else:
        check(src, '"', 'Missing String Terminator')
    return ret

def read_num(src):
    val = ''
    while src and (src[-1].isdecimal() or src[-1] in '.Ee-+'):
        val += src.pop()
    try:
        start_idx = val.startswith('-') or val.startswith('+')
        return int(val) if val[start_idx:].isdecimal() else float(val)
    except ValueError:pass
    assert False, "Failed to Parse Number"

def read_object(src):
    check(src, '{', 'Missing Object Initializer')
    src[:] = ''.join(src).rstrip()
    obj = {}
    while src and src[-1] != '}':
        key = read_str(src)
        src[:] = ''.join(src).rstrip()
        check(src, ':', 'Invalid Seperator in Object')
        value = read(src)
        obj[key] = value
        src[:] = ''.join(src).rstrip()
        if check(src, ',}', 'Missing Object Terminator or Seperator') == '}':
            break
        src[:] = ''.join(src).rstrip()
    else:
        check(src, "}", 'Missing Object Terminator')
    return obj

def read_array(src):
    check(src, '[', 'Missing Array Initializer')
    src[:] = ''.join(src).rstrip()
    arr = []
    while src and src[-1] != ']':
        value = read(src)
        arr.append(value)
        src[:] = ''.join(src).rstrip()
        if check(src, ',]', 'Missing Array Terminator or Seperator') == ']':
            break
    else:
        check(src, ']', 'Missing Array Terminator')
    return arr

def read(src):
    src[:] = ''.join(src).rstrip()
    assert src, "Not Enough Data"
    if src[-1].isdecimal() or src[-1] in '-+.':
        return read_num(src)
    elif src[-1] in 'tfn':
        assert len(src) >= 4, 'Not Enough Characters For Constant'
        const = ''.join(src.pop() for _ in range(4))
        if const == 'true':
            return True
        elif const == 'null':
            return None
        next = check(src, 'e', "Invalid Constant")
        if const + next == 'false':
            return False
        assert False, "Failed to Parse Constant"
    parse_func = {
        '"': read_str,
        '{': read_object,
        '[': read_array
    }.get(src[-1])
    if parse_func:
        return parse_func(src)
    assert False, "Invalid JSON"

def parse(inp):
    src = [*inp[::-1]]
    ret = read(src)
    src = ''.join(src).rstrip()
    assert not src, "Extra Data Remaining"
    return ret
