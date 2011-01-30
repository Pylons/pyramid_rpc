import unittest
import sys

from pyramid import testing

class TestXMLRPCMarshal(unittest.TestCase):
    def _callFUT(self, value):
        from pyramid_rpc.xmlrpc import xmlrpc_marshal
        return xmlrpc_marshal(value)
        
    def test_xmlrpc_marshal_normal(self):
        data = 1
        marshalled = self._callFUT(data)
        import xmlrpclib
        self.assertEqual(marshalled, xmlrpclib.dumps((data,),
                                                     methodresponse=True))

    def test_xmlrpc_marshal_fault(self):
        import xmlrpclib
        fault = xmlrpclib.Fault(1, 'foo')
        data = self._callFUT(fault)
        self.assertEqual(data, xmlrpclib.dumps(fault))

class TestParseXMLRPCRequest(unittest.TestCase):
    def _callFUT(self, request):
        from pyramid_rpc.xmlrpc import parse_xmlrpc_request
        return parse_xmlrpc_request(request)

    def test_normal(self):
        import xmlrpclib
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
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(): pass
        wrapped = decorator(foo)
        self.failUnless(wrapped is foo)
        settings = call_venusian(venusian)
        self.assertEqual(len(settings), 1)
        self.assertEqual(settings[0]['permission'], None)
        self.assertEqual(settings[0]['context'], None)
        self.assertEqual(settings[0]['request_type'], None)
        self.assertEqual(settings[0]['name'], 'foo')
        self.assertEqual(settings[0]['route_name'], 'RPC2')

class TestXMLRPCEndPoint(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        from pyramid.threadlocal import get_current_registry
        self.registry = get_current_registry()

    def tearDown(self):
        testing.cleanUp()

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
        from pyramid.interfaces import IViewClassifier
        from pyramid.exceptions import NotFound
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

class DummyVenusianInfo(object):
    scope = 'notaclass'
    module = sys.modules['pyramid_rpc.tests']
    codeinfo = None

class DummyVenusian(object):
    def __init__(self, info=None):
        if info is None:
            info = DummyVenusianInfo()
        self.info = info
        self.attachments = []

    def attach(self, wrapped, callback, category=None):
        self.attachments.append((wrapped, callback, category))
        return self.info

class DummyConfig(object):
    def __init__(self):
        self.settings = []

    def add_view(self, **kw):
        self.settings.append(kw)

class DummyVenusianContext(object):
    def __init__(self):
        self.config = DummyConfig()
        
def call_venusian(venusian):
    context = DummyVenusianContext()
    for wrapped, callback, category in venusian.attachments:
        callback(context, None, None)
    return context.config.settings
