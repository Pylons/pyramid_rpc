import unittest
from pyramid import testing

class TestMapplyViewMapper(unittest.TestCase):
    def _makeOne(self, **kw):
        from pyramid_rpc.mapper import MapplyViewMapper
        return MapplyViewMapper(**kw)

    def test___call__isfunc_no_rpc_args_no_attr(self):
        data = '123'
        def view(request):
            return data
        context = testing.DummyResource()
        request = testing.DummyRequest()
        mapper = self._makeOne()
        result = mapper(view)(context, request)
        self.assertEqual(result, data)

    def test___call__isfunc_no_rpc_args_with_attr(self):
        view = lambda *arg: 'wrong'
        data = '123'
        def foo(request):
            return data
        view.foo = foo
        context = testing.DummyResource()
        request = testing.DummyRequest()
        mapper = self._makeOne(attr='foo')
        result = mapper(view)(context, request)
        self.assertEqual(result, data)

    def test___call__isfunc_with_rpc_args(self):
        def view(request, a, b):
            return a, b
        context = testing.DummyResource()
        request = testing.DummyRequest()
        request.rpc_args = ('a', 'b')
        mapper = self._makeOne()
        result = mapper(view)(context, request)
        self.assertEqual(result, ('a', 'b'))

    def test___call__isfunc_with_rpc_args_and_matchdict(self):
        def view(request, a, b, c=1):
            return a, b, c
        context = testing.DummyResource()
        request = testing.DummyRequest()
        request.rpc_args = ('a', 'b')
        request.matchdict = dict(c='2')
        mapper = self._makeOne()
        result = mapper(view)(context, request)
        self.assertEqual(result, ('a', 'b', '2'))

    def test___call__isclass_no_rpc_args_no_attr(self):
        data = '123'
        class view(object):
            def __init__(self, request):
                pass
            def __call__(self):
                return data
        context = testing.DummyResource()
        request = testing.DummyRequest()
        mapper = self._makeOne()
        result = mapper(view)(context, request)
        self.assertEqual(result, data)
        self.assertEqual(request.__view__.__class__, view)

    def test___call__isclass_no_rpc_args_with_attr(self):
        view = lambda *arg: 'wrong'
        data = '123'
        class view(object):
            def __init__(self, request):
                pass
            def index(self):
                return data
        context = testing.DummyResource()
        request = testing.DummyRequest()
        mapper = self._makeOne(attr='index')
        result = mapper(view)(context, request)
        self.assertEqual(result, data)
        self.assertEqual(request.__view__.__class__, view)

    def test___call__isclass_with_rpc_args(self):
        class view(object):
            def __init__(self, request):
                pass
            def __call__(self, a, b):
                return a, b
        context = testing.DummyResource()
        request = testing.DummyRequest()
        request.rpc_args = ('a', 'b')
        mapper = self._makeOne()
        result = mapper(view)(context, request)
        self.assertEqual(result, ('a', 'b'))

    def test___call__isclass_with_rpc_args_and_matchdict(self):
        class view(object):
            def __init__(self, request):
                pass
            def __call__(self, a, b, c=1):
                return a, b, c
        context = testing.DummyResource()
        request = testing.DummyRequest()
        request.rpc_args = ('a', 'b')
        request.matchdict = dict(c='2')
        mapper = self._makeOne()
        result = mapper(view)(context, request)
        self.assertEqual(result, ('a', 'b', '2'))

    def test_mapply_toomanyargs(self):
        def aview(one, two): pass
        mapper = self._makeOne()
        self.assertRaises(TypeError, mapper.mapply, aview, (1, 2, 3), {})

    def test_mapply_all_kwarg_arg_omitted(self):
        def aview(one, two): pass
        mapper = self._makeOne()
        self.assertRaises(TypeError, mapper.mapply, aview, (), dict(one=1))

    def test_mapply_all_kwarg_arg_omitted_with_default(self):
        def aview(one, two=2):
            return one, two
        mapper = self._makeOne()
        result = mapper.mapply(aview, (), dict(one=1))
        self.assertEqual(result, (1, 2))

    def test_mapply_all_kwarg(self):
        def aview(one, two):
            return one, two
        mapper = self._makeOne()
        result = mapper.mapply(aview, (), dict(one=1, two=2))
        self.assertEqual(result, (1, 2))

    def test_mapply_instmethod(self):
        mapper = self._makeOne()
        result = mapper.mapply(self._aview, ('a',), {})
        self.assertEqual(result, 'a')

    def test_mapply_inst(self):
        class Foo(object):
            def __call__(self, a):
                return a
        foo = Foo()
        mapper = self._makeOne()
        result = mapper.mapply(foo, ('a',), {})
        self.assertEqual(result, 'a')

    def _aview(self, a):
        return a
