import sys
import unittest
import warnings
import xmlrpclib

from pyramid import testing

from webtest import TestApp

class TestXMLRPCMarshal(unittest.TestCase):
    def _callFUT(self, value):
        from pyramid_rpc.xmlrpc import xmlrpc_marshal
        return xmlrpc_marshal(value)
        
    def test_xmlrpc_marshal_normal(self):
        data = 1
        marshalled = self._callFUT(data)
        self.assertEqual(marshalled, xmlrpclib.dumps((data,),
                                                     methodresponse=True))

    def test_xmlrpc_marshal_fault(self):
        fault = xmlrpclib.Fault(1, 'foo')
        data = self._callFUT(fault)
        self.assertEqual(data, xmlrpclib.dumps(fault))

class TestParseXMLRPCRequest(unittest.TestCase):
    def _callFUT(self, request):
        from pyramid_rpc.xmlrpc import parse_xmlrpc_request
        return parse_xmlrpc_request(request)

    def test_normal(self):
        param = 1
        packet = xmlrpclib.dumps((param,), methodname='__call__')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)
        params, method = self._callFUT(request)
        self.assertEqual(params[0], param)
        self.assertEqual(method, '__call__')

    def test_toobig(self):
        request = testing.DummyRequest()
        request.content_length = 1 << 24
        self.assertRaises(ValueError, self._callFUT, request)

class TestXMLRPCViewDecorator(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from pyramid_rpc import xmlrpc_view
        return xmlrpc_view

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def test_call_function(self):
        decorator = self._makeOne()
        settings = []
        def view_config(**kw):
            settings.append(kw)
            return lambda x: x
        def foo(): pass
        wrapped = decorator(foo, view_config=view_config)
        self.assertTrue(wrapped is foo)
        self.assertEqual(len(settings), 1)
        self.assertEqual(settings[0]['name'], 'foo')
        self.assertEqual(settings[0]['route_name'], 'RPC2')

class TestXMLRPCEndPoint(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        from pyramid.threadlocal import get_current_registry
        self.registry = get_current_registry()
        warnings.filterwarnings('ignore')

    def tearDown(self):
        testing.cleanUp()
        warnings.resetwarnings()

    def _getTargetClass(self):
        from pyramid_rpc.xmlrpc import xmlrpc_endpoint
        return xmlrpc_endpoint

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()

    def _registerRouteRequest(self, name):
        from pyramid.interfaces import IRouteRequest
        from pyramid.request import route_request_iface
        iface = route_request_iface(name)
        self.registry.registerUtility(iface, IRouteRequest, name=name)
        return iface

    def _registerView(self, app, name, classifier, req_iface, ctx_iface):
        from pyramid.interfaces import IView
        self.registry.registerAdapter(
            app, (classifier, req_iface, ctx_iface), IView, name)
    
    def _makeDummyRequest(self):
        from pyramid.testing import DummyRequest
        return DummyRequest()
    
    def test_xmlrpc_endpoint(self):
        from pyramid.interfaces import IViewClassifier
        view = DummyView({'name': 'Smith'})
        rpc2_iface = self._registerRouteRequest('RPC2')
        self._registerView(view, 'echo', IViewClassifier, rpc2_iface, None)
        
        xmlrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = DummyXMLBody
        request.matched_route = DummyRoute('RPC2')
        response = xmlrpc_endpoint(request)
        self.assertEqual(response.content_type, 'text/xml')
        self.assertEqual(response.content_length, 202)
    
    def test_xmlrpc_endpoint_not_found(self):
        xmlrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = DummyXMLBody
        request.matched_route = DummyRoute('RPC2')
        response = xmlrpc_endpoint(request)
        self.assertEqual(response.message, "No method of that name was found.")


DummyXMLBody = """<?xml version="1.0" encoding="ISO-8859-1"?>
<methodCall>
   <methodName>echo</methodName>
   <params>
       <param>
	    <value><int>13</int></value>
       </param>
   </params>
</methodCall>
"""


class DummyRoute:
    def __init__(self, route_name):
        self.name = route_name

class DummyView:
    def __init__(self, response, raise_exception=None):
        self.response = response
        self.raise_exception = raise_exception

    def __call__(self, context, request):
        self.context = context
        self.request = request
        return self.response

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

    def test_method_decorator(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('api', '/api/xmlrpc')
        config.scan('pyramid_rpc.tests.fixtures.xmlrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'create', (2, 3))
        self.assertEqual(resp, {'create': 'bob'})

    def test_method_decorator_with_method_from_view_name(self):
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('api', '/api/xmlrpc')
        config.scan('pyramid_rpc.tests.fixtures.xmlrpc_method_default')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = self._callFUT(app, 'create', (2, 3))
        self.assertEqual(resp, {'create': 'bob'})

    def test_method_decorator_with_no_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.xmlrpc')
        config.add_xmlrpc_endpoint('api', '/api/xmlrpc')
        self.assertRaises(ConfigurationError, config.scan,
                          'pyramid_rpc.tests.fixtures.xmlrpc_no_endpoint')

