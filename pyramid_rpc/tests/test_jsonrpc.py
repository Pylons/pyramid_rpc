import unittest
import sys

from pyramid import testing

try:
    import json
except ImportError:
    import simplejson as json

class TestJSONRPCEndPoint(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        from pyramid.threadlocal import get_current_registry
        self.registry = get_current_registry()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from pyramid_rpc.jsonrpc import jsonrpc_endpoint
        return jsonrpc_endpoint

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
    
    def test_jsonrpc_endpoint(self):
        from pyramid.interfaces import IViewClassifier
        view = DummyView({'name': 'Smith'})
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(view, 'echo', IViewClassifier, rpc_iface, None)
        
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = DummyJSONBody
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.body)
        self.assertEqual({"jsonrpc": "2.0", "id": "echo-rpc", "result": {'name': 'Smith'}}, data)
    
    def test_jsonrpc_endpoint_not_found(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid.exceptions import NotFound
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = DummyJSONBody
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], -32601)

    def test_jsonrpc_endpoint_parse_error(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid.exceptions import NotFound
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = "]"
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], -32700)

    def test_jsonrpc_endpoint_internal_error(self):
        from pyramid.interfaces import IViewClassifier
        def error_view(request):
            raise Exception
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(error_view, 'error', IViewClassifier, rpc_iface, None)

        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = ErrorJSONBody
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], -32603)

    def test_jsonrpc_endpoint_invalid_request(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid.exceptions import NotFound
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = "[]"
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], -32600)

    def test_jsonrpc_endpoint_invalid_version(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid.exceptions import NotFound
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = '{"jsonrpc": "1.0"}'
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], -32600)

DummyJSONBody = """{
    "jsonrpc": "2.0",
    "id": "echo-rpc",
    "method": "echo",
    "params": [13]
}
"""

ErrorJSONBody = """{
    "jsonrpc": "2.0",
    "id": "error-rpc",
    "method": "error",
    "params": [13]
}
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
