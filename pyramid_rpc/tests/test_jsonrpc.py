import unittest
import sys

from pyramid import testing

try:
    import json
except ImportError:
    import simplejson as json

class TestJSONRPCMapper(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid_rpc.jsonrpc import JsonRpcViewMapper
        return JsonRpcViewMapper

    def _makeOne(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)

    def test_implements(self):
        from pyramid.interfaces import IViewMapperFactory
        from pyramid.interfaces import IViewMapper
        cls  = self._getTargetClass()
        self.assertTrue(IViewMapperFactory.providedBy(cls))
        self.assertTrue(IViewMapper.implementedBy(cls))
        target = cls()
        self.assertTrue(IViewMapper.providedBy(target))

    def test_view_callable_with_list(self):

        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.jsonrpc_args = [1, 2]
        context = object()
        result = view_callable(context, request)
        self.assertEqual(result, 3)

    def test_view_callable_with_dict(self):
        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.jsonrpc_args = dict(a=3, b=4)
        context = object()
        result = view_callable(context, request)
        self.assertEqual(result, 7)

    def test_view_callable_with_invalid_args(self):
        from pyramid_rpc.jsonrpc import JsonRpcParamsInvalid

        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.jsonrpc_args = []
        context = object()
        self.assertRaises(JsonRpcParamsInvalid, view_callable, context, request)

    def test_view_callable_with_invalid_keywords(self):
        from pyramid_rpc.jsonrpc import JsonRpcParamsInvalid

        target = self._makeOne()
        view_callable = target(dummy_view)
        request = testing.DummyRequest()
        request.jsonrpc_args = {}
        context = object()
        self.assertRaises(JsonRpcParamsInvalid, view_callable, context, request)

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

    def test_jsonrpc_notification(self):
        from pyramid.interfaces import IViewClassifier
        view = DummyView({'name': 'Smith'})
        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(view, 'echo', IViewClassifier, rpc_iface, None)
        
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = NotificationJSONBody
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual('', response.body)
    
    def test_jsonrpc_endpoint_not_found(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcMethodNotFound
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = DummyJSONBody
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcMethodNotFound.code)

    def test_jsonrpc_endpoint_parse_error(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid.exceptions import NotFound
        from pyramid_rpc.jsonrpc import JsonRpcParseError
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = "]"
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcParseError.code)

    def test_jsonrpc_endpoint_internal_error(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcInternalError
        def error_view(context, request):
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
        self.assertEqual(data['error']['code'], JsonRpcInternalError.code)

    def test_jsonrpc_endpoint_invalid_response(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcInternalError
        def invalid_view(context, request):
            return object()

        rpc_iface = self._registerRouteRequest('JSON-RPC')
        self._registerView(invalid_view, 'invalid', IViewClassifier, rpc_iface, None)

        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = InvalidJSONBody
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcInternalError.code)

    def test_jsonrpc_endpoint_empty_request(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = ""
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

    def test_jsonrpc_endpoint_invalid_request(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = "[]"
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

    def test_jsonrpc_endpoint_invalid_version(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = '{"jsonrpc": "1.0"}'
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

    def test_jsonrpc_endpoint_no_method(self):
        from pyramid.interfaces import IViewClassifier
        from pyramid_rpc.jsonrpc import JsonRpcRequestInvalid
        jsonrpc_endpoint = self._makeOne()
        request = self._makeDummyRequest()
        request.body = '{"jsonrpc": "2.0"}'
        request.content_length = len(request.body)
        request.matched_route = DummyRoute('JSON-RPC')
        response = jsonrpc_endpoint(request)
        data = json.loads(response.body)
        self.assertEqual(data['error']['code'], JsonRpcRequestInvalid.code)

class FunctionalTest(unittest.TestCase):

    def test_it(self):
        from pyramid.config import Configurator
        from pyramid_rpc.jsonrpc import jsonrpc_endpoint
        from pyramid_rpc.jsonrpc import JsonRpcViewMapper
        config = Configurator()
        config.add_route('JSON-RPC', 'apis/rpc', view=jsonrpc_endpoint)
        def dummy_rpc(request, a, b):
            return a + b
        config.add_view(route_name='JSON-RPC', name='dummy.rpc', view=dummy_rpc, mapper=JsonRpcViewMapper)
        app = config.make_wsgi_app()
        import webtest
        app = webtest.TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy_rpc', 'params': [2, 3], 'id': 'test'}
        body = json.dumps(params)
        res = app.post('/apis/rpc', params=body, content_type='application/json')
        data = json.loads(res.body)
        self.assertEqual(data['id'], 'test')
        self.assertEqual(data['jsonrpc'], '2.0')
        self.assertEqual(data['result'], 5)


DummyJSONBody = """{
    "jsonrpc": "2.0",
    "id": "echo-rpc",
    "method": "echo",
    "params": [13]
}
"""

NotificationJSONBody = """{
    "jsonrpc": "2.0",
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

InvalidJSONBody = """{
    "jsonrpc": "2.0",
    "id": "error-rpc",
    "method": "invalid",
    "params": [13]
}
"""

class DummyRoute:
    def __init__(self, route_name):
        self.name = route_name

def dummy_view(request, a, b):
    return a + b

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

# class DummyVenusian(object):
#     def __init__(self, info=None):
#         if info is None:
#             info = DummyVenusianInfo()
#         self.info = info
#         self.attachments = []
# 
#     def attach(self, wrapped, callback, category=None):
#         self.attachments.append((wrapped, callback, category))
#         return self.info
# 
# class DummyConfig(object):
#     def __init__(self):
#         self.settings = []
# 
#     def add_view(self, **kw):
#         self.settings.append(kw)
# 
# class DummyVenusianContext(object):
#     def __init__(self):
#         self.config = DummyConfig()
#         
# def call_venusian(venusian):
#     context = DummyVenusianContext()
#     for wrapped, callback, category in venusian.attachments:
#         callback(context, None, None)
#     return context.config.settings
