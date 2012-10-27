import sys
import unittest

from pyramid import testing

from webtest import TestApp

from pyramid_rpc.compat import xmlrpclib

class TestXMLRPCIntegration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, app, method, params):
        resp = app.post('/api/xmlrpc', content_type='text/xml',
                        params=xmlrpclib.dumps(params, methodname=method))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'text/xml')
        return xmlrpclib.loads(resp.body)[0][0]

    def test_add_xmlrpc_method_with_no_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        self.assertRaises(ConfigurationError,
                          config.add_xmlrpc_method,
                          lambda r: None, method='dummy')

    def test_add_xmlrpc_method_with_no_method(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
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

