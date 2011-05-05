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
        self.assertEqual(response.content_length, 73)
    
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
        assert data['error']['code'] == -32601


DummyJSONBody = """{
    "jsonrpc": "2.0",
    "id": null,
    "method": "echo",
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
