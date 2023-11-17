import itertools
import readline
import ast

dispatch = {}
def register(ops, argc, precedence=None):
    def inner(func):
        for op in ops:
            dispatch[op] = (func, argc, precedence)
        return func
    return inner

@register(['~', '!', 'not'], argc=1, precedence=1)
def unary_not(val):
    return not val

@register(['⋀', 'A', 'and', '&'], argc=2, precedence=2)
def binary_and(v1, v2):
    return v1 and v2

@register(['∨', 'V', 'or', '|'], argc=2, precedence=3)
def binary_or(v1, v2):
    return v1 or v2

@register(['→', '->'], argc=2, precedence=4)
def binary_conditional(v1, v2):
    return not v1 or v2

@register(['↔', '<->', '='], argc=2, precedence=5)
def binary_biconditional(v1, v2):
    return v1 == v2

@register(['<'], argc=2)
def binary_lt(v1, v2):
    return v1 < v2

@register(['≤', '<='], argc=2)
def binary_lteq(v1, v2):
    return v1 <= v2

@register(['>'], argc=2)
def binary_gt(v1, v2):
    return v1 > v2

@register(['≥', '>='], argc=2)
def binary_gteq(v1, v2):
    return v1 >= v2

@register(['⊕', '^', 'xor'], argc=2)
def binary_xor(v1, v2):
    return v1 ^ v2

@register(['!='], argc=2)
def binary_neq(v1, v2):
    return v1 != v2

@register([None], argc=1)
def nop(v1):
    return v1

class ParsingError(Exception):
    def __init__(self, msg, idx):
        super().__init__(msg)
        self.idx = idx

def build_tree_inner(stmt, vars, opener=None, args=None):
    current_op = None
    args = args or []
    closed = False
    while stmt:
        tok, idx = stmt.pop(0)
        if tok.isspace():
            continue
        if tok in ')]}' and opener is None:
            # we must be in a precedence recursive call, put back and bail
            stmt.insert(0, (tok, idx))
            break
        elif tok == {
            '(': ')',
            '[': ']',
            '{': '}'
        }.get(opener):
            # we just closed a container, set flag and bail
            closed = True
            break
        elif tok in '({[':
            # we just entered new container, recurse
            args.append(build_tree_inner(stmt, vars, tok))
        elif tok in dispatch:
            # we just found an operator
            if current_op:
                # we already have an operator, handle unary ops and precedence
                _, new_ac, new_p = dispatch.get(tok, (None, 0, None))
                _, ac, p = dispatch.get(current_op, (None, 0, None))
                if len(args) != ac:
                    # we have a new op, but not enough args for current op
                    # it should be a unary op
                    # put back new op, and recurse to get next arg
                    if new_ac != 1:
                        raise ParsingError(f'Invalid Token: {idx=}', idx)
                    stmt.insert(0, (tok, idx))
                    args.append(build_tree_inner(stmt, vars))
                    continue
                else:
                    if new_p is None or p is None:
                        # need to apply precedence manually
                        raise ParsingError(f'One or more ambiguous operators has appeared, apply precedence with parenthesis: {idx=}', idx)
                    if new_p < p:
                        # new op has higher precedence
                        # put back new op, and recurse with last arg
                        stmt.insert(0, (tok, idx))
                        args[-1] = build_tree_inner(stmt, vars, None, [args[-1]])
                        continue
                    else:
                        # new op has lower precedence
                        # repace args with our current op and args
                        # continue with new op
                        args[:] = [[current_op, *args]]
            current_op = tok
        elif tok.isalpha():
            # variable token, add it to args and vars
            vars.add(tok)
            args.append(tok)
        else:
            raise ParsingError(f'Invalid Token: {idx=}', idx)
    # we are either out of tokens, or bailed
    do_op, ac, p = dispatch.get(current_op)
    if ac != len(args):
        raise ParsingError(f'Invalid number of args for op: {current_op}, {idx=}', idx)
    if opener and not closed:
        # enforces that containers must be closed
        raise ParsingError(f'Bracket: {opener} never closed, {idx=}', idx)
    return [current_op, *args]

def tokenize_inner(stmt):
    chars = [*stmt]
    while chars:
        let = chars.pop(0)
        idx = len(stmt) - len(chars) - 1
        if let.isspace():
            continue
        elif let in '{[()]}':
            yield let, idx
        elif any(key and (let + ''.join(chars)).startswith(key) for key in dispatch):
            for key in sorted(dispatch, key=lambda k:0 if k is None else len(k))[::-1]:
                if key and (let + ''.join(chars)).startswith(key):
                    yield let + ''.join(chars.pop(0) for _ in range(len(key) - 1)), idx
                    break
        elif let.isalnum():
            while chars and chars[0].isalnum():
                let += chars.pop(0)
            yield let, idx
        else:
            raise ParsingError(f'Invalid Token: {idx=}', idx)

def tokenize(stmt):
    if not stmt:
        raise ParsingError('no input to tokenizer', -1)
    try:
        return [*tokenize_inner(stmt)]
    except ParsingError as e:
        msg = '\n\t' + e.args[0]
        msg += '\n\t' + stmt + '\n'
        msg += '\t' + (' ' * e.idx) + '^\n'
        e.args = (msg, *e.args[1:])
        raise

def build_tree(stmt, tokens):
    vars = set()
    msg = None
    try:
        return build_tree_inner(tokens, vars), list(vars)
    except ParsingError as e:
        msg = '\n\t' + e.args[0]
        msg += '\n\t' + stmt + '\n'
        msg += '\t' + (' ' * e.idx) + '^\n'
        e.args = (msg, *e.args[1:])
        raise
    finally:
        if tokens and msg is None:
            raise ParsingError('tokens remaining after parsing', -1)

def run_tree(tree, vars):
    op, *args = tree
    vals = []
    for arg in args.copy():
        if isinstance(arg, list):
            vals.append(run_tree(arg, vars))
        else:
            vals.append(vars[arg])
    do_op, ac, p = dispatch[op]
    if ac != len(vals):
        raise RuntimeError(f'Invalid number of args for op: {op}')
    return do_op(*vals)

def format_table(tbl):
    out = []
    rows = [r for r in tbl if r]
    if rows:
        for cidx in range(len(rows[0])):
            largest = None
            for r in rows:
                if largest is None or len(r[cidx]) > largest:
                    largest = len(r[cidx])
            for r in rows:
                r[cidx] += ' ' * (largest - len(r[cidx]))
    for i, row in enumerate(tbl):
        if row:
            out.append('┃' + '┃'.join(row) + '┃')
        else:
            out.append('┣' + (''.join('╋' if c in '┃╋' else '━' for c in out[-1][1:-1]) if out else '') + '┫')
    out.insert(0, '┏' + (''.join('┳' if c in '┃╋' else '━' for c in out[0][1:-1]) if out else '') + '┓')
    out.append('┗' + (''.join('┻' if c in '┃╋' else '━' for c in out[-1][1:-1]) if out else '') + '┛')
    return '\n'.join(out)

def build_table(stmt, tree, vars, args):
    lines = []
    lines.append([*vars, stmt])
    lines.append(None)
    for vals in args:
        res = repr(run_tree(tree, {k: v for k, v in zip(vars, vals)}))
        lines.append([*map(repr, vals), res])
    print(format_table(lines))

def truth_table(stmt):
    tokens = tokenize(stmt)
    tree, vars = build_tree(stmt, tokens.copy())
    args = itertools.product(*[[True, False]] * len(vars))
    build_table(stmt, tree, sorted(vars), args)

def eval_statement(stmt, **vals):
    tokens = tokenize(stmt)
    tree, vars = build_tree(stmt, tokens.copy())
    build_table(stmt, tree, sorted(vars), [[vals.get(v) for v in sorted(vars)]])

def dump_tree(tree, level=0, comma=False):
    op, *args = tree
    func, *_ = dispatch.get(op)
    print('  '*level, f'{func.__name__}(', sep='')
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            print('  '*(level + 1), arg, end=(',' if ((i + 1) != len(args)) else '') + '\n', sep='')
        else:
            dump_tree(arg, level+1, ((i + 1) != len(args)))
    print('  '*level, ')'+(',' if comma else ''), sep='')

def ttr():
    while True:
        try:
            inp = input('?> ')
            if inp == 'exit':
                break
            stmt, *args = inp.split(',')
            if args:
                adct = {}
                for a in args:
                    if '=' not in a:
                        raise Exception('One or more arguments is formated incorrectly: [varname]=[value]')
                    k, v = a.strip().split('=')
                    try:
                        adct[k] = ast.literal_eval(v)
                    except:
                        raise Exception('Malformed value')
                eval_statement(stmt, **adct)
            else:
                truth_table(stmt)
        except EOFError:
            print()
            break
        except Exception as e:
            print(e)
    print('exiting...')

if __name__ == '__main__':
    ttr()
