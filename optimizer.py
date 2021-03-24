# STRATEGIES
# - builtin methods:
#   set.add, SET_ADD
#   set.update, SET_UPDATE
#   list.append, LIST_APPEND
#   list.extend, LIST_EXTEND
#   dict.update, DICT_UPDATE

'''
Optimizes some basic constructs to use native bytecode
'''

import dis

patterns = {
    (set, 'add'): dis.opmap['SET_ADD'],
    (set, 'update'): dis.opmap['SET_UPDATE'],
    (list, 'append'): dis.opmap['LIST_APPEND'],
    (list, 'extend'): dis.opmap['LIST_EXTEND'],
    (dict, 'update'): dis.opmap['DICT_UPDATE']
}

def infer_types(code_obj):
    flags = {
        'SET_ADD': set,
        'SET_UPDATE': set,
        'LIST_APPEND': list,
        'LIST_EXTEND': list,
        'DICT_UPDATE': dict,
        'BUILD_LIST': list,
        'BUILD_MAP': dict,
        'BUILD_SET': set,
        'BUILD_TUPLE': tuple
    }
    typ_map = {}
    instrucs = [*dis.get_instructions(code_obj)]
    for idx, inst in enumerate(instrucs):
        if inst.opname == 'STORE_FAST' and (typ := flags.get(instrucs[idx-2].opname if instrucs[idx-1].opname == 'DUP_TOP' else instrucs[idx-1].opname)):
            # look for `STORE_FAST` preceded by any `flag`
            # if a name is used twice for 2 types, then we don't optimize for that name
            if inst.argval not in typ_map:
                typ_map[inst.argval] = typ
            else:
                typ_map[inst.argval] = None
    for key, val in typ_map.copy().items():
        if val is None:
            del typ_map[key]
    return typ_map

def optimize_for(code_obj, name, typ):
    co_code = bytearray(code_obj.co_code)
    for idx in range(0, len(co_code), 2):
        op, arg = co_code[idx:idx + 2]
        if dis.opname[op] == 'CALL_METHOD' and arg ==  1:
            sidx = idx
            while dis.opname[co_code[sidx]] != 'LOAD_METHOD':
                sidx -= 2
            if (op_name := dis.opname[co_code[sidx - 2]]).startswith('LOAD_') and op_name != 'LOAD_CONST':
                if op_name == 'LOAD_FAST':
                    if code_obj.co_varnames[co_code[sidx - 1]] != name:
                        continue
                else:
                    if code_obj.co_names[co_code[sidx - 1]] != name:
                        continue
                meth_name = code_obj.co_names[co_code[sidx + 1]]
                if new_op := patterns.get((typ, meth_name)):
                    # replace `LOAD_METHOD` with `NOP`
                    # replace `CALL_METHOD` with `new_op`
                    co_code[sidx] = dis.opmap['NOP']
                    co_code[idx] = new_op

    return code_obj.replace(co_code=bytes(co_code))

def optimize(*args, **kwargs):
    def wp(func):
        func.__typs__ = kwargs | func.__annotations__ | infer_types(func)
        for name, typ in func.__typs__.items():
            func.__code__ = optimize_for(func.__code__, name, typ)
        return func
    if len(args)==1:
        return wp(args[0])
    return wp

@optimize
def f(x: list):
    for i in x.copy():
        x.append(i)
    return x

from timeit import timeit

graph = {
  'A' : ['B','C'],
  'B' : ['D', 'E'],
  'C' : ['F'],
  'D' : [],
  'E' : ['F'],
  'F' : []
}

@optimize
def opt_bfs(graph=graph, node='A'):
  visited = [node]
  queue = [node]

  while queue:
    s = queue.pop(0)
    #print(s, end=" ")

    for neighbour in graph[s]:
      if neighbour not in visited:
        visited.append(neighbour)
        queue.append(neighbour)

print('opt:', timeit(opt_bfs))

def reg_bfs(graph=graph, node='A'):
  visited = [node]
  queue = [node]

  while queue:
    s = queue.pop(0)
    #print(s, end=" ")

    for neighbour in graph[s]:
      if neighbour not in visited:
        visited.append(neighbour)
        queue.append(neighbour)

print('reg:', timeit(reg_bfs))
