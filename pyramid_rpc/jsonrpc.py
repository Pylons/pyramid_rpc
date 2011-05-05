try:
    import json
except ImportError:
    import simplejson as json
import logging

import venusian

from pyramid.response import Response

from pyramid.view import view_config

from pyramid_rpc.api import view_lookup

__all__ = ['jsonrpc_endpoint', 'jsonrpc_view']

log = logging.getLogger(__name__)

JSONRPC_VERSION = '2.0'

class JsonRpcError(BaseException):
    code = None
    message = None

    def __init__(self, data=None):
        self.data = data

#    def __str__(self):
#        return str(self.code) + ': ' + self.message

    def as_dict(self):
        """Return a dictionary representation of this object for
        serialization in a JSON-RPC response."""
        error = dict(code=self.code,
                     message=self.message)
#        if self.data:
#            error['data'] = self.data

        return error

class JsonRpcParseError(JsonRpcError):
    code = -32700
    message = 'parse error'

class JsonRpcRequestInvalid(JsonRpcError):
    code = -32600
    message = 'invalid request'

class JsonRpcMethodNotFound(JsonRpcError):
    code = -32601
    message = 'method not found'

class JsonRpcParamsInvalid(JsonRpcError):
    code = -32602
    message = 'invalid params'

class JsonRpcInternalError(JsonRpcError):
    code = -32603
    message = 'internal error'

def jsonrpc_response(data, id=None):
    """ Marshal a Python data structure into a webob ``Response``
    object with a body that is a JSON string suitable for use as a
    JSON-RPC response with a content-type of ``application/json``
    and return the response."""

    if id is None:
        return Response(content_type="application/json")

#    if isinstance(data, Exception):
#        return jsonrpc_error_response(data, id)

    out = {
        'jsonrpc' : JSONRPC_VERSION,
        'id' : id,
        'result' : data,
    }
    try:
        body = json.dumps(out)
    except Exception, e:
        return jsonrpc_error_response(JsonRpcInternalError(), id)

    response = Response(body)
    response.content_type = 'application/json'
    response.content_length = len(body)
    return response

def jsonrpc_error_response(error, id=None):
    """ Marshal a Python Exception into a webob ``Response``
    object with a body that is a JSON string suitable for use as
    a JSON-RPC response with a content-type of ``application/json``
    and return the response."""

    if not isinstance(error, JsonRpcError):
        error = JsonRpcInternalError()

    body = json.dumps({
        'jsonrpc' : JSONRPC_VERSION,
        'id' : id,
        'error' : error.as_dict(),
    })

    response = Response(body)
    response.content_type = 'application/json'
    response.content_length = len(body)
    return response

#class jsonrpc_view(object):
#    """ This decorator may be used with pyramid view callables to enable them
#    to respond to JSON-RPC method calls.
#    
#    If ``method`` is not supplied, then the callable name will be used for
#    the method name. If ``route_name`` is not supplied, it is assumed that
#    the appropriate route was added to the application's config (named
#    'JSON-RPC' by default).
#    
#    """
#    venusian = venusian # for testing injection
#    def __init__(self, method=None, route_name='JSON-RPC', **kwargs):
#        self.method = method
#        self.route_name = route_name
#        self.kwargs = kwargs
#    
#    def __call__(self, wrapped):
#        view_config.venusian = self.venusian
#        name = self.kwargs.pop('name', None)
#        method_name = self.method or name or wrapped.__name__
#        method_name = method_name.replace('.', '_')
#        return view_config(route_name=self.route_name, name=method_name,
#                           **self.kwargs)(wrapped)

def jsonrpc_endpoint(request):
    """A base view to be used with add_route to setup a JSON-RPC dispatch
    endpoint
    
    Use this view with ``add_route`` to setup a JSON-RPC endpoint, for
    example::
        
        config.add_route('JSON-RPC', '/apis/jsonrpc', view=jsonrpc_endpoint)
    
    JSON-RPC methods should then be registered with ``add_view`` using the
    route_name of the endpoint, the name as the jsonrpc method name. Or for
    brevity, the :class:`~pyramid_rpc.jsonrpc.jsonrpc_view` decorator can be
    used.
    
    For example, to register an jsonrpc method 'list_users'::
    
        @jsonrpc_view()
        def list_users(request):
            json_params = request.jsonrpc_args
            return {'users': [...]}
    
    Existing views that return a dict can be used with jsonrpc_view.
    
    """
    environ = request.environ

    length = request.content_length
    if length == 0:
        return jsonrpc_error_response(JsonRpcRequestInvalid())

    try:
        body = json.loads(request.body)
    except ValueError:
        return jsonrpc_error_response(JsonRpcParseError())

    if not isinstance(body, dict):
        return jsonrpc_error_response(JsonRpcRequestInvalid())

    rpc_id = body.get('id')
    rpc_args = body.get('params', [])
    rpc_method = body.get('method')
    rpc_version = body.get('jsonrpc')

    if rpc_version != JSONRPC_VERSION:
        return jsonrpc_error_response(JsonRpcRequestInvalid(), rpc_id)

    if not rpc_method:
        return jsonrpc_error_response(JsonRpcMethodNotFound(), rpc_id)

    method_name = rpc_method.replace('_', '.')
    view_callable = view_lookup(request, method_name)
    log.debug('view callable %r found for method %r', view_callable, rpc_method)
    if not view_callable:
        return jsonrpc_error_response(JsonRpcMethodNotFound(), rpc_id)

    request.jsonrpc_args = rpc_args

    try:
        data = view_callable(request.context, request)
        return jsonrpc_response(data, rpc_id)
    except Exception, e:
        return jsonrpc_error_response(e, rpc_id)

