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

class TestXMLRPResponse(unittest.TestCase):
    def _callFUT(self, value):
        from pyramid_rpc.xmlrpc import xmlrpc_response
        return xmlrpc_response(value)
        
    def test_xmlrpc_response(self):
        import xmlrpclib
        data = 1
        response = self._callFUT(data)
        self.assertEqual(response.content_type, 'text/xml')
        self.assertEqual(response.body, xmlrpclib.dumps((1,),
                                                        methodresponse=True))
        self.assertEqual(response.content_length, len(response.body))
        self.assertEqual(response.status, '200 OK')
        
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

class DummyVenusianInfo(object):
    scope = 'notaclass'
    module = sys.modules['pyramid_rpc.tests']

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
