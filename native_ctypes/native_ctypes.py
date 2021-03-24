from load_addr import *
from util import *
from bases import *


class c_char(c_data):
    _size_ = 1
    _format_ = 'c'

class c_ubyte(c_data):
    _size_ = 1
    _format_ = 'B'

class c_byte(c_data):
    _size_ = 1
    _format_ = 'b'

class c_ushort(c_data):
    _size_ = 2
    _format_ = 'H'

class c_short(c_data):
    _size_ = 2
    _format_ = 'h'

class c_uint(c_data):
    _size_ = 4
    _format_ = 'I'

class c_int(c_data):
    _size_ = 4
    _format_ = 'i'

class c_ulong(c_data):
    _size_ = 8
    _format_ = 'L'

class c_long(c_data):
    _size_ = 8
    _format_ = 'l'

class c_float(c_data):
    _size_ = 4
    _format_ = 'f'

class c_double(c_data):
    _size_ = 8
    _format_ = 'd'

class c_size_t(c_data):
    _size_ = PTR_SIZE
    _format_ = 'N'

class c_ssize_t(c_data):
    _size_ = PTR_SIZE
    _format_ = 'n'

class c_void_p(c_data):
    _size_ = PTR_SIZE
    _format_ = 'P'
    def __getitem__(self, idx):
        return type(self).from_address(self.addr + (self._size_ * idx)).value

    def __setitem__(self, idx, value):
        type(self).from_address(self.addr + (self._size_ * idx)).value = value

    def __add__(self, n):
        return type(self).from_address(self.addr + (self._size_ * n))

    def __sub__(self, n):
        return type(self).from_address(self.addr - (self._size_ * n))

class c_ptr(c_void_p):
    _typed_ = True

class c_char_p(c_void_p):
    def _get_(self):
        value = b''
        addr = super()._get_()
        if addr:
            arr = (c_char*None).from_address(addr)
            value = b''.join(arr.value)
        return value

    def _set_(self, value):
        o_addr = super()._get_()
        if is_allocated(o_addr):
            free(o_addr)
        new = (c_ubyte*len(value))(value) # iter(value) yields ints, not bytes
        super()._set_(addressof(new))

    def _del_(self):
        addr = super()._get_()
        if is_allocated(addr):
            free(o_addr)
        super()._del_()

class py_object(c_void_p):
    def _get_(self):
        if not self.is_null():
            addr = super()._get_()
            return load_addr(addr)
        return NULL

    def _set_(self, value):
        if not self.is_null():
            decref(self._get_())
        incref(value)
        super()._set_(id(value))

class PyObject(c_struct):
    ob_refcnt: c_ssize_t
    ob_base: py_object

class PyVarObject(PyObject):
    ob_size: c_ssize_t

class FloatObj(PyObject):
    ob_fval: c_double

class ListObj(PyVarObject):
    ob_item: field(lambda inst:c_ptr[py_object*inst.ob_size], c_ptr._size_)
    allocated: c_ulong

class TupleObj(PyVarObject):
    ob_item: field(lambda inst:py_object*inst.ob_size)

class LongObj(PyVarObject):
    ob_digit: field(lambda inst:c_int*abs(inst.ob_size))

class TypeObj(PyVarObject):
    tp_name: c_char_p
    tp_basicsize: c_long
    tp_itemsize: c_long
    tp_dealloc: c_void_p
    tp_vectorcall_offset: c_ssize_t
    tp_getattr: c_void_p
    tp_setattr: c_void_p
    tp_as_async: c_ptr[anon('PyAsyncMethods', c_struct,
        am_await=c_void_p,
        am_aiter=c_void_p,
        am_anext=c_void_p,
        am_send=c_void_p
    )]
    tp_repr: c_void_p
    tp_as_number: c_ptr[anon('PyNumberMethods', c_struct,
        nb_add=c_void_p,
        nb_subtract=c_void_p,
        nb_multiply=c_void_p,
        nb_remainder=c_void_p,
        nb_divmod=c_void_p,
        nb_power=c_void_p,
        nb_negative=c_void_p,
        nb_positive=c_void_p,
        nb_absolute=c_void_p,
        nb_bool=c_void_p,
        nb_invert=c_void_p,
        nb_lshift=c_void_p,
        nb_rshift=c_void_p,
        nb_and=c_void_p,
        nb_xor=c_void_p,
        nb_or=c_void_p,
        nb_int=c_void_p,
        nb_reserved=c_void_p,
        nb_float=c_void_p,
        nb_inplace_add=c_void_p,
        nb_inplace_subtract=c_void_p,
        nb_inplace_multiply=c_void_p,
        nb_inplace_remainder=c_void_p,
        nb_inplace_power=c_void_p,
        nb_inplace_lshift=c_void_p,
        nb_inplace_rshift=c_void_p,
        nb_inplace_and=c_void_p,
        nb_inplace_xor=c_void_p,
        nb_inplace_or=c_void_p,
        nb_floor_divide=c_void_p,
        nb_true_divide=c_void_p,
        nb_inplace_floor_divide=c_void_p,
        nb_inplace_true_divide=c_void_p,
        nb_index=c_void_p,
        nb_matrix_multiply=c_void_p,
        nb_inplace_matrix_multiply=c_void_p
    )]
    tp_as_sequence: c_ptr[anon('PySequenceMethods', c_struct,
        sq_length=c_void_p,
        sq_concat=c_void_p,
        sq_repeat=c_void_p,
        sq_item=c_void_p,
        was_sq_slice=c_void_p,
        sq_ass_item=c_void_p,
        was_sq_ass_slice=c_void_p,
        sq_contains=c_void_p,
        sq_inplace_concat=c_void_p,
        sq_inplace_repeat=c_void_p
    )]
    tp_as_mapping: c_ptr[anon('PyMappingMethods', c_struct,
        mp_length=c_void_p,
        mp_subscript=c_void_p,
        mp_ass_subscript=c_void_p
    )]
    tp_hash: c_void_p
    tp_call: c_void_p
    tp_str: c_void_p
    tp_getattro: c_void_p
    tp_setattro: c_void_p
    tp_as_buffer: c_ptr[anon('PyBufferProcs', c_struct,
         bf_getbuffer=c_void_p,
         bf_releasebuffer=c_void_p
    )]
    tp_flags: c_ulong
    tp_doc: c_char_p
    tp_traverse: c_void_p
    tp_clear: c_void_p
    tp_richcompare: c_void_p
    tp_weaklistoffset: c_long
    tp_iter: c_void_p
    tp_iternext: c_void_p
    tp_methods: c_ptr[anon('PyMethodDef', c_struct,
        name=c_char_p,
        meth=c_void_p,
        flags=c_long,
        doc=c_char_p
    )*None]
    tp_members: c_ptr[anon('PyMemberDef', c_struct,
        name=c_char_p,
        type=c_long,
        offset=c_long,
        flags=c_long,
        doc=c_char_p
    )*None]
    tp_getset: c_ptr[anon('PyGetSetDef', c_struct,
        name=c_char_p,
        get=c_void_p,
        set=c_void_p,
        doc=c_char_p,
        closure=c_void_p
    )*None]
    tp_base: py_object
    tp_dict: py_object
    tp_descr_get: c_void_p
    tp_descr_set: c_void_p
    tp_dictoffset: c_long
    tp_init: c_void_p
    tp_alloc: c_void_p
    tp_new: c_void_p
    tp_free: c_void_p
    tp_is_gc: c_void_p
    tp_bases: py_object
    tp_mro: py_object
    tp_cache: py_object
    tp_subclasses: py_object
    tp_weaklist: py_object
    tp_del: c_void_p
    tp_version_tag: c_ulong
    tp_finalize: c_void_p
    tp_vectorcall: c_void_p

def PyType_Modified(typ):
    if (typ.__flags__ & (1 << 19)) == 0:
        return

    for ref in typ.__subclasses__():
        PyType_Modified(ref)
    TypeObj.from_address(id(typ)).tp_flags &= ~(1 << 19)

def determine_contents_type(self):
    base_cls = self.ob_base
    if '__slots__' in vars(base_cls):
        return anon(c_struct, **{
            n: py_object for n in base_cls.__slots__
        })
    else:
        return anon(c_struct, cls_dict=py_object, tp_weaklist=c_void_p)

class UserCls(PyObject):
    cls_contents: field(determine_contents_type)
