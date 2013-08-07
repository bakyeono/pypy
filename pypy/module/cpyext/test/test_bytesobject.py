from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.bytesobject import new_empty_str, PyBytesObject
from pypy.module.cpyext.api import PyObjectP, PyObject, Py_ssize_tP
from pypy.module.cpyext.pyobject import Py_DecRef, from_ref, make_ref

import py
import sys

class AppTestBytesObject(AppTestCpythonExtensionBase):
    def test_bytesobject(self):
        module = self.import_extension('foo', [
            ("get_hello1", "METH_NOARGS",
             """
                 return PyBytes_FromStringAndSize(
                     "Hello world<should not be included>", 11);
             """),
            ("get_hello2", "METH_NOARGS",
             """
                 return PyBytes_FromString("Hello world");
             """),
            ("test_Size", "METH_NOARGS",
             """
                 PyObject* s = PyBytes_FromString("Hello world");
                 int result = 0;

                 if(PyBytes_Size(s) == 11) {
                     result = 1;
                 }
                 if(s->ob_type->tp_basicsize != sizeof(void*)*4)
                     result = 0;
                 Py_DECREF(s);
                 return PyBool_FromLong(result);
             """),
            ("test_Size_exception", "METH_NOARGS",
             """
                 PyObject* f = PyFloat_FromDouble(1.0);
                 Py_ssize_t size = PyBytes_Size(f);

                 Py_DECREF(f);
                 return NULL;
             """),
             ("test_is_bytes", "METH_VARARGS",
             """
                return PyBool_FromLong(PyBytes_Check(PyTuple_GetItem(args, 0)));
             """)])
        assert module.get_hello1() == b'Hello world'
        assert module.get_hello2() == b'Hello world'
        assert module.test_Size()
        raises(TypeError, module.test_Size_exception)

        assert module.test_is_bytes(b"")
        assert not module.test_is_bytes(())

    def test_bytes_buffer_init(self):
        module = self.import_extension('foo', [
            ("getbytes", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 char* c;
                 Py_ssize_t len;

                 s = PyBytes_FromStringAndSize(NULL, 4);
                 if (s == NULL)
                    return NULL;
                 t = PyBytes_FromStringAndSize(NULL, 3);
                 if (t == NULL)
                    return NULL;
                 Py_DECREF(t);
                 c = PyBytes_AsString(s);
                 c[0] = 'a';
                 c[1] = 'b';
                 c[3] = 'c';
                 return s;
             """),
            ])
        s = module.getbytes()
        assert len(s) == 4
        assert s == b'ab\x00c'



    def test_AsString(self):
        module = self.import_extension('foo', [
            ("getbytes", "METH_NOARGS",
             """
                 PyObject* s1 = PyBytes_FromStringAndSize("test", 4);
                 char* c = PyBytes_AsString(s1);
                 PyObject* s2 = PyBytes_FromStringAndSize(c, 4);
                 Py_DECREF(s1);
                 return s2;
             """),
            ])
        s = module.getbytes()
        assert s == b'test'

    def test_py_bytes_as_string(self):
        module = self.import_extension('foo', [
            ("bytes_as_string", "METH_VARARGS",
             '''
             return PyBytes_FromStringAndSize(PyBytes_AsString(
                       PyTuple_GetItem(args, 0)), 4);
             '''
            )])
        assert module.bytes_as_string(b"huheduwe") == b"huhe"

    def test_py_bytes_as_string_None(self):
        module = self.import_extension('foo', [
            ("string_None", "METH_VARARGS",
             '''
             return PyBytes_AsString(Py_None);
             '''
            )])
        raises(TypeError, module.string_None)

    def test_AsStringAndSize(self):
        module = self.import_extension('foo', [
            ("getbytes", "METH_NOARGS",
             """
                 PyObject* s1 = PyBytes_FromStringAndSize("te\\0st", 5);
                 char *buf;
                 Py_ssize_t len;
                 if (PyBytes_AsStringAndSize(s1, &buf, &len) < 0)
                     return NULL;
                 if (len != 5) {
                     PyErr_SetString(PyExc_AssertionError, "Bad Length");
                     return NULL;
                 }
                 if (PyBytes_AsStringAndSize(s1, &buf, NULL) >= 0) {
                     PyErr_SetString(PyExc_AssertionError, "Should Have failed");
                     return NULL;
                 }
                 PyErr_Clear();
                 Py_DECREF(s1);
                 Py_INCREF(Py_None);
                 return Py_None;
             """),
            ])
        module.getbytes()


class TestBytes(BaseApiTest):
    def test_bytes_resize(self, space, api):
        py_str = new_empty_str(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_str.c_buffer[0] = 'a'
        py_str.c_buffer[1] = 'b'
        py_str.c_buffer[2] = 'c'
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyBytes_Resize(ar, 3)
        py_str = rffi.cast(PyBytesObject, ar[0])
        assert py_str.c_size == 3
        assert py_str.c_buffer[1] == 'b'
        assert py_str.c_buffer[3] == '\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyBytes_Resize(ar, 10)
        py_str = rffi.cast(PyBytesObject, ar[0])
        assert py_str.c_size == 10
        assert py_str.c_buffer[1] == 'b'
        assert py_str.c_buffer[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_Concat(self, space, api):
        ref = make_ref(space, space.wrapbytes('abc'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref
        api.PyBytes_Concat(ptr, space.wrapbytes('def'))
        assert space.bytes_w(from_ref(space, ptr[0])) == 'abcdef'
        api.PyBytes_Concat(ptr, space.w_None)
        assert not ptr[0]
        ptr[0] = lltype.nullptr(PyObject.TO)
        api.PyBytes_Concat(ptr, space.wrapbytes('def')) # should not crash
        lltype.free(ptr, flavor='raw')

    def test_ConcatAndDel(self, space, api):
        ref1 = make_ref(space, space.wrapbytes('abc'))
        ref2 = make_ref(space, space.wrapbytes('def'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref1
        api.PyBytes_ConcatAndDel(ptr, ref2)
        assert space.bytes_w(from_ref(space, ptr[0])) == 'abcdef'
        assert ref2.c_ob_refcnt == 0
        Py_DecRef(space, ptr[0])
        ptr[0] = lltype.nullptr(PyObject.TO)
        ref2 = make_ref(space, space.wrapbytes('foo'))
        api.PyBytes_ConcatAndDel(ptr, ref2) # should not crash
        assert ref2.c_ob_refcnt == 0
        lltype.free(ptr, flavor='raw')

    def test_asbuffer(self, space, api):
        bufp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        lenp = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')

        w_text = space.wrapbytes("text")
        assert api.PyObject_AsCharBuffer(w_text, bufp, lenp) == 0
        assert lenp[0] == 4
        assert rffi.charp2str(bufp[0]) == 'text'

        lltype.free(bufp, flavor='raw')
        lltype.free(lenp, flavor='raw')

    def test_eq(self, space, api):
        assert 1 == api._PyBytes_Eq(space.wrapbytes("hello"), space.wrapbytes("hello"))
        assert 0 == api._PyBytes_Eq(space.wrapbytes("hello"), space.wrapbytes("world"))

    def test_join(self, space, api):
        w_sep = space.wrapbytes('<sep>')
        w_seq = space.newtuple([space.wrapbytes('a'), space.wrapbytes('b')])
        w_joined = api._PyBytes_Join(w_sep, w_seq)
        assert space.bytes_w(w_joined) == 'a<sep>b'

    def test_FromObject(self, space, api):
        w_obj = space.wrapbytes("test")
        assert space.eq_w(w_obj, api.PyBytes_FromObject(w_obj))
        w_obj = space.call_function(space.w_bytearray, w_obj)
        assert space.eq_w(w_obj, api.PyBytes_FromObject(w_obj))
        w_obj = space.wrap(u"test")
        assert api.PyBytes_FromObject(w_obj) is None
        api.PyErr_Clear()
