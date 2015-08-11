import sys
import unittest

from pyramid import testing

from webtest import TestApp

from pyramid_rpc.compat import PY3
from pyramid_rpc.compat import xmlrpclib

class TestXMLRPCIntegration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, app, method, params):
        if PY3: # pragma: no cover
            xml = xmlrpclib.dumps(params, methodname=method).encode('utf-8')
        else:
            xml = xmlrpclib.dumps(params, methodname=method)
        resp = app.post('/api/xmlrpc', content_type='text/xml', params=xml)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'text/xml')
        return xmlrpclib.loads(resp.body)[0][0]

    def test_add_xmlrpc_method_with_undefined_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        self.assertRaises(ConfigurationError,
                          config.add_xmlrpc_method,
                          lambda r: None, endpoint='rpc', method='dummy')

    def test_add_xmlrpc_method_with_missing_endpoint_param(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        self.assertRaises(ConfigurationError,
                          config.add_xmlrpc_method,
                          lambda r: None, method='dummy')

    def test_add_xmlrpc_method_with_no_method(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        self.assertRaises(ConfigurationError,
                          config.add_xmlrpc_method,
                          lambda r: None, endpoint='rpc')

    def test_it(self):
        def view(request, a, b):
            return {'a': a, 'b': b}
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', (2, 3))
        self.assertEqual(resp, {'a': 2, 'b': 3})

    def test_it_with_no_mapper(self):
        def view(request):
            return request.rpc_args[0]
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy',
                                  mapper=None)
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', (2, 3))
        self.assertEqual(resp, 2)

    def test_it_with_multiple_methods(self):
        def view(request, a, b):
            return a
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        config.add_xmlrpc_method(lambda r: 'fail',
                                  endpoint='rpc', method='dummy2')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', (2, 3))
        self.assertEqual(resp, 2)

    def test_it_with_no_method(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        try:
            self._callFUT(app, None, (2, 3))
        except xmlrpclib.Fault:
            exc = sys.exc_info()[1] # 2.5 compat
            self.assertEqual(exc.faultCode, -32601)
        else: # pragma: no cover
            raise AssertionError

    def test_it_with_no_params(self):
        def view(request):
            self.assertEqual(request.rpc_args, ())
            return 'no params'
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', ())
        self.assertEqual(resp, 'no params')

    def test_it_with_invalid_method(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        try:
            self._callFUT(app, 'dummy', (2, 3))
        except xmlrpclib.Fault:
            exc = sys.exc_info()[1] # 2.5 compat
            self.assertEqual(exc.faultCode, -32601)
        else: # pragma: no cover
            raise AssertionError

    def test_it_with_invalid_body(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = app.post('/api/xmlrpc', content_type='text/xml',
                        params='<')
        try:
            xmlrpclib.loads(resp.body)
        except xmlrpclib.Fault:
            exc = sys.exc_info()[1] # 2.5 compat
            self.assertEqual(exc.faultCode, -32700)
        else: # pragma: no cover
            raise AssertionError

    def test_it_with_general_exception(self):
        def view(request, a, b):
            raise Exception
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        try:
            self._callFUT(app, 'dummy', (2, 3))
        except xmlrpclib.Fault:
            exc = sys.exc_info()[1] # 2.5 compat
            self.assertEqual(exc.faultCode, -32500)
        else: # pragma: no cover
            raise AssertionError

    def test_it_with_cls_view(self):
        class view(object):
            def __init__(self, request):
                self.request = request

            def foo(self, a, b):
                return [a, b]
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy',
                                  attr='foo')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', (2, 3))
        self.assertEqual(resp, [2, 3])

    def test_it_with_default_args(self):
        def view(request, a, b, c='bar'):
            return [a, b, c]
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', (2, 3))
        self.assertEqual(resp, [2, 3, 'bar'])

    def test_it_with_missing_args(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(lambda r, a, b: a,
                                  endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        try:
            self._callFUT(app, 'dummy', (2,))
        except xmlrpclib.Fault:
            exc = sys.exc_info()[1] # 2.5 compat
            self.assertEqual(exc.faultCode, -32602)
        else: # pragma: no cover
            raise AssertionError

    def test_it_with_too_many_args(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(lambda r, a, b: a,
                                  endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        try:
            self._callFUT(app, 'dummy', (2, 3, 4))
        except xmlrpclib.Fault:
            exc = sys.exc_info()[1] # 2.5 compat
            self.assertEqual(exc.faultCode, -32602)
        else: # pragma: no cover
            raise AssertionError

    def test_it_with_decorator(self):
        def view(request):
            return 'foo'
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        dummy_decorator = DummyDecorator()
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy',
                                 decorator=dummy_decorator)
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', ())
        self.assertEqual(resp, 'foo')
        self.assertTrue(dummy_decorator.called)

    def test_it_with_default_mapper(self):
        def view(request):
            return request.rpc_args
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc', default_mapper=None)
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', ('a', 'b', 'c'))
        self.assertEqual(resp, ['a', 'b', 'c'])

    def test_override_default_mapper(self):
        from pyramid_rpc.mapper import MapplyViewMapper
        def view(request, a, b, c):
            return (a, b, c)
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc', default_mapper=None)
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy',
                                 mapper=MapplyViewMapper)
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', ('a', 'b', 'c'))
        self.assertEqual(resp, ['a', 'b', 'c'])

    def test_it_with_default_renderer(self):
        def view(request, a, b, c):
            return 'bar'
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        dummy_renderer = DummyRenderer(('foo',))
        config.add_renderer('xmlrpc', dummy_renderer)
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc',
                                   default_renderer='xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', ('a', 'b', 'c'))
        self.assertEqual(resp, 'foo')
        self.assertEqual(dummy_renderer.called, True)

    def test_override_default_renderer(self):
        def view(request):
            return 'bar'
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        dummy_renderer = DummyRenderer(('foo',))
        dummy_renderer2 = DummyRenderer(('baz',))
        config.add_renderer('xmlrpc', dummy_renderer)
        config.add_renderer('xmlrpc2', dummy_renderer2)
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc',
                                   default_renderer='xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy',
                                 renderer='xmlrpc2')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'dummy', ())
        self.assertEqual(resp, 'baz')
        self.assertEqual(dummy_renderer.called, False)
        self.assertEqual(dummy_renderer2.called, True)

    def test_nonascii_request(self):
        def view(request, a):
            return a
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('rpc', '/api/xmlrpc')
        config.add_xmlrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        val = b'S\xc3\xa9bastien'.decode('utf-8')
        resp = self._callFUT(app, 'dummy', (val,))
        self.assertEqual(resp, val)


class DummyDecorator(object):
    called = False

    def __call__(self, view):
        def wrapper(context, request):
            self.called = True
            return view(context, request)
        return wrapper

class DummyRenderer(object):
    called = False

    def __init__(self, result):
        self.result = result

    def __call__(self, info):
        def _render(value, system):
            self.called = True
            system['request'].response.content_type = 'text/xml'
            return xmlrpclib.dumps(self.result, methodresponse=True)
        return _render
