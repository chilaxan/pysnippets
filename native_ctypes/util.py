from .load_addr import *

def incref(obj):
	getmem(id(obj), PTR_SIZE).cast('n')[0] += 1

def decref(obj):
	getmem(id(obj), PTR_SIZE).cast('n')[0] -= 1

def mem_utils():
	cache = {}
	def alloc(size):
		# returns the address of the allocated memory
		if size < 0:
			raise Exception(f'cannot alloc {size} bytes')
		array = bytearray(size)
		ptr = int.from_bytes(getmem(id(array) + (PTR_SIZE * 4), PTR_SIZE), 'little')
		cache[ptr] = array
		return ptr

	def free(ptr):
		if is_allocated(ptr):
			del cache[ptr]
		else:
			raise Exception(f'{ptr} is not an allocated address')

	def is_allocated(ptr):
		return ptr in cache

	return alloc, free, is_allocated

alloc, free, is_allocated = mem_utils()

def cast(obj, typ):
	if hasattr(obj, '_addr') and (obj._addr is not None):
		return typ.from_address(obj.addr)
	raise Exception(f'unable to cast {obj} to {typ}')

def memcpy(dest, src, n):
	getmem(dest, n)[:] = getmem(src, n)

def check(attr):
	def attr_checker(func):
		def wrapped(self, *args, **kwargs):
			if hasattr(self, attr) and getattr(self, attr):
				return func(self, *args, **kwargs)
			raise Exception(f'{self} does not support {attr}')
		return wrapped
	return attr_checker

def csizeof(obj):
	return obj._size_

def addressof(obj):
	return obj.addr

rec = type('Rec', (), {'__repr__':lambda s:'...'})()

def flatten(value, level=0):
	if level >= 3:
		return rec
	if hasattr(value, 'value') and hasattr(value, '_addr'):
		value = flatten(value.value, level + 1)
	if isinstance(value, list):
		lst = []
		for subval in value:
			lst.append(flatten(subval, level + 1))
		value = lst
	elif isinstance(value, dict):
		dct = {}
		for key, subval in value.items():
			dct[key] = flatten(subval, level + 1)
		value = dct
	return value

def replace(self, **kwargs):
	co_keys = [k for k in dir(type(self)) if 'co_' in k]
	co_args = [
		'argcount', 'posonlyargcount', 'kwonlyargcount',
		'nlocals', 'stacksize', 'flags', 'codestring',
		'constants', 'names', 'varnames', 'filename',
		'name', 'firstlineno', 'lnotab', 'freevars', 'cellvars'
	]
	alts = {
		'co_consts': 'constants',
		'co_code': 'codestring'
	}
	return type(self)(*[v for k,v in sorted([
			(alts.get(key, key[3:]), kwargs.get(key, getattr(self, key))) for key in co_keys
	], key=lambda i:co_args.index(i[0]))])
