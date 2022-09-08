from .load_addr import *
from .util import *

type_cache = {}

NULL = type('<NULL>',(),{'__repr__':lambda s:'<NULL>', '__bool__':lambda s:False})()

class c_meta(type):
    def __repr__(cls):
        return cls.__name__

    @check('_typed_')
    def __getitem__(cls, typ):
        if (cls, typ) in type_cache:
            return type_cache[cls, typ]
        def _get_(self):
            if cls.is_null(self):
                return NULL
            addr = cls._get_(self)
            return typ.from_address(addr)

        def _set_(self, value):
            if hasattr(value, 'addr'):
                value = addressof(value)
            cls._set_(self, value)

        return type_cache.setdefault(
            (cls, typ),
            type(
                f'{cls}[{typ}]',
                (cls.__base__,), {
                    '_typ_':typ,
                    '_size_':cls._size_,
                    '_format_':cls._format_,
                    '_get_':_get_,
                    '_set_':_set_
                }
            )
        )

    def __mul__(cls, length):
        if cls._size_ == -1 and length is None:
            raise TypeError(f'({cls}*{length}) is invalid')
        if (cls, length) in type_cache:
            return type_cache[cls, length]

        def at_idx(self, idx):
            return cls.from_address(self.addr + (cls._size_ * idx))

        def _get_(self, slc=slice(None)):
            return [self[idx] for idx in range(*slc.indices(len(self)))]

        def _set_(self, iterable):
            if iterable:
                for idx, val in zip(range(len(self)), iterable):
                    self[idx] = val

        def __len__(self):
            idx = length
            if idx is None:
                idx = 0
                while not self.at_idx(idx).is_null():
                    idx += 1
            return idx

        def __getitem__(self, idx):
            if isinstance(idx, slice):
                return self._get_(idx)
            return self.at_idx(idx).value

        def __setitem__(self, idx, value):
            if isinstance(idx, slice):
                for jdx, val in zip(range(*idx.indices(len(self))), value):
                    self.at_idx(jdx).value = val
            else:
                self.at_idx(idx).value = value

        return type_cache.setdefault(
            (cls, length),
            type(
                f'({cls}*{length})',
                (c_data,), {
                    'length':length,
                    '_typ_':cls,
                    '_size_':(cls._size_ * length) if length else -1,
                    '__len__':__len__,
                    '__getitem__':__getitem__,
                    '__setitem__':__setitem__,
                    'at_idx':at_idx,
                    '_get_':_get_,
                    '_set_':_set_
                }
            )
        )

class c_data(metaclass=c_meta):
    def __init__(self, value=NULL, sizes=()): # `sizes` is used for dynamic structs
        self._pre_init_(sizes)
        if self._size_ < 0:
            raise TypeError(f'unable to alloc {type(self)} with size of {self._size_}')
        self._addr = alloc(self._size_)
        try:
            self.value = value
        except ValueError:
            del self.value
            raise

    def __repr__(self):
        if getattr(self, '_addr', None) is not None:
            return f'{type(self)}({flatten(self.value)!r})'
        return f'{type(self)}(<freed>)'

    def _pre_init_(self, args):
        pass

    def _raw_(self):
        _size_ = self._size_
        if _size_ == -1 and hasattr(self, '__len__'):
            _size_ = len(self)
        return getmem(self.addr, _size_)

    def _get_(self):
        return self._raw_().cast(self._format_)[0]

    def _set_(self, value):
        try:
            self._raw_().cast(self._format_)[0] = value
        except ValueError:
            raise ValueError(f'unable to set {type(self)} to {value}') from None

    def _del_(self):
        self.value = NULL
        if is_allocated(self.addr):
            free(self.addr)
        self._addr = None

    @property
    def addr(self):
        if self._addr is not None:
            return self._addr
        raise MemoryError('operation on freed memory')

    @classmethod
    def from_address(cls, addr):
        if not isinstance(addr, int):
            raise TypeError('integer expected')
        self = cls.__new__(cls)
        self._addr = addr
        return self

    @property
    def value(self):
        return self._get_()

    @value.setter
    def value(self, value):
        if value is not NULL:
            self._set_(value)
        else:
            raw = self._raw_()
            raw[:raw.nbytes] = b'\x00' * raw.nbytes

    @value.deleter
    def value(self):
        self._del_()

    def is_null(self):
        return sum(self._raw_()) == 0

class field:
    def __init__(self, get_typ, _size_=0, _name_='<field>'):
        self.get_typ = get_typ
        self._size_ = _size_
        self.__name__ = _name_

class complex_data(c_data):
    def __getattr__(self, attr):
        if attr not in [fld for fld, _ in self._fields_]:
            return super().__getattribute__(attr)
        else:
            raw = self.by_name(attr)
            if hasattr(type(raw), 'length'):
                return raw
            if type(raw).__base__ == c_data:
                return raw.value
            else:
                return raw

    def __setattr__(self, attr, value):
        if attr not in [fld for fld, _ in self._fields_]:
            super().__setattr__(attr, value)
        else:
            raw = self.by_name(attr)
            if type(raw).__base__ == c_data:
                raw.value = value
            else:
                assert raw._size_ == value._size_
                memcpy(raw.addr, value.addr, raw._size_)

    def __dir__(self):
        return super().__dir__() + [fld for fld, _ in self._fields_]

    def _get_(self):
        return {fld:getattr(self,fld) for fld, _ in self._fields_}

    def _set_(self, value):
        if value:
            for key, typ in self._fields_:
                if val := value.get(key):
                    setattr(self, key, val)

class c_struct(complex_data):
    def __init_subclass__(cls):
        cls._fields_ = getattr(cls.__base__, '_fields_', []) + \
                       vars(cls).get('_fields_', [*getattr(cls, '__annotations__', {}).items()])
        _size_ = 0
        for _, typ in cls._fields_:
            if not typ._size_:
                cls._size_ = -1
                return
            _size_ += typ._size_
        cls._size_ = _size_

    def _pre_init_(self, sizes):
        if self._size_ == -1:
            # this struct has dynamic sized fields, so we need more info to init
            _size_ = 0
            for _, typ in self._fields_:
                if typ._size_:
                    _size_ += typ._size_
                else:
                    if sizes:
                        inc, *sizes = sizes
                        _size_ += inc
                    else:
                        raise TypeError(f'not enough sizes for {type(self)}')
            self._size_ = _size_
        if sizes:
            raise TypeError(f'too many sizes for {type(self)}')

    def by_name(self, name):
        offset = 0
        for fld_name, typ in self._fields_:
            if fld_name == name:
                if isinstance(typ, field):
                    typ = typ.get_typ(self)
                return typ.from_address(self.addr + offset)
            offset += typ._size_
        raise NameError(f'{name} not in {type(self)}')

class c_union(complex_data):
    def __init_subclass__(cls):
        cls._fields_ = getattr(cls.__base__, '_fields_', []) + \
                       vars(cls).get('_fields_', [*getattr(cls, '__annotations__', {}).items()])
        _size_ = 0
        for _, typ in cls._fields_:
            if isinstance(typ, field):
                raise NotImplementedError(f'{cls} does not support {type(typ).__name__}')
            if _size_ < typ._size_:
                _size_ = typ._size_
        cls._size_ = _size_

    def by_name(self, name):
        for fld_name, typ in self._fields_:
            if fld_name == name:
                return typ.from_address(self.addr)
        raise NameError(f'{name} not in {type(self)}')

def anon(*args, **kwargs):
    name, typ = args
    return type(
        f'{name}',
        (typ,),
        {'__annotations__':kwargs}
    )
