try:
    import json
except ImportError:
    import simplejson as json
import logging
import urllib

import venusian
from zope.interface import providedBy

from pyramid.response import Response

from pyramid.interfaces import IRequest
from pyramid.interfaces import IRouteRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier

from pyramid.httpexceptions import HTTPLengthRequired
from pyramid.view import view_config

__all__ = ['jsonrpc_endpoint', 'jsonrpc_view', 'JSONRPCError',
           'JSONRPC_PARSE_ERROR', 'JSONRPC_INVALID_REQUEST',
           'JSONRPC_METHOD_NOT_FOUND', 'JSONRPC_INVALID_PARAMS',
           'JSONRPC_INTERNAL_ERROR']

log = logging.getLogger(__name__)

JSONRPC_VERSION = '2.0'

class JSONRPCError(BaseException):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.data = None

    def _get_message(self):
        return self._message

    def _set_message(self, message):
        self._message = message

    message = property(_get_message, _set_message)

    def __str__(self):
        return str(self.code) + ': ' + self.message

    def as_dict(self):
        """Return a dictionary representation of this object for
        serialization in a JSON-RPC response."""
        error = dict(code=self.code,
                     message=self.message)
        if self.data:
            error['data'] = self.data

        return error


JSONRPC_PARSE_ERROR = JSONRPCError(-32700, "Parse error")
JSONRPC_INVALID_REQUEST = JSONRPCError( -32600, "Invalid Request")
JSONRPC_METHOD_NOT_FOUND = JSONRPCError( -32601, "Method not found")
JSONRPC_INVALID_PARAMS = JSONRPCError( -32602, "Invalid params")
JSONRPC_INTERNAL_ERROR = JSONRPCError( -32603, "Internal error")


def jsonrpc_marshal(data, id):
    """ Marshal a Python data structure into a JSON string suitable
    for use as an JSON-RPC response and return the document.  If
    ``data`` is a ``JSONRPCError`` instance, it will be marshalled
    into a suitable JSON-RPC error object."""
    out = {
        'jsonrpc' : JSONRPC_VERSION,
        'id' : id,
    }
    if isinstance(data, JSONRPCError):
        out['error'] = data.as_dict()
    else:
        out['result'] = data or ''
    return json.dumps(out)

def jsonrpc_response(data, id=None):
    """ Marshal a Python data structure into a webob ``Response``
    object with a body that is a JSON string suitable for use as an
    JSON-RPC response with a content-type of ``application/json`` and return
    the response."""
    body = jsonrpc_marshal(data, id)
    response = Response(body)
    response.content_type = 'application/json'
    response.content_length = len(body)
    if isinstance(data, JSONRPCError):
        response.set_header('x-tm-abort', 'true')
    return response

def find_jsonrpc_view(request, method):
    """ Search for a registered JSON-RPC view for the endpoint."""
    registry = request.registry
    adapters = registry.adapters

    if method is None: return None

    method = method.replace('.', '_')

    # Hairy view lookup stuff below, woo!
    request_iface = registry.queryUtility(
        IRouteRequest, name=request.matched_route.name,
        default=IRequest)
    context_iface = providedBy(request.context)

    view_callable = adapters.lookup(
        (IViewClassifier, request_iface, context_iface),
        IView, name=method, default=None)

    return view_callable

class jsonrpc_view(object):
    """ This decorator may be used with pyramid view callables to enable them
    to repsond to JSON-RPC method calls.
    
    If ``method`` is not supplied, then the callable name will be used for
    the method name. If ``route_name`` is not supplied, it is assumed that
    the appropriate route was added to the application's config (named
    'RPC3').
    
    """
    venusian = venusian # for testing injection
    def __init__(self, method=None, route_name='RPC3',
                 context=None, permission=None, custom_predicates=()):
        self.method = method
        self.route_name = route_name
        self.context = context
        self.permission = permission
        self.custom_predicates = custom_predicates
    
    def __call__(self, wrapped):
        view_config.venusian = self.venusian
        method_name = self.method or wrapped.__name__
        method_name = method_name.replace('.', '_')
        return view_config(route_name=self.route_name, name=method_name,
                           context=self.context, permission=self.permission,
                           custom_predicates=self.custom_predicates)(wrapped)

def jsonrpc_endpoint(request):
    """A base view to be used with add_route to setup a JSON-RPC dispatch
    endpoint
    
    Use this view with ``add_route`` to setup a JSON-RPC endpoint, for
    example::
        
        config.add_route('RPC3', '/apis/RPC3', view=jsonrpc_endpoint)
    
    JSON-RPC methods should then be registered with ``add_view`` using the
    route_name of the endpoint, the name as the jsonrpc method name. Or for
    brevity, the :class:`~pyramid_rpc.jsonrpc.jsonrpc_view` decorator can be
    used.
    
    For example, to register an jsonrpc method 'list_users'::
    
        @jsonrpc_view()
        def list_users(request):
            json_params = request.jsonrpc_params
            return {'users': [...]}
    
    Existing views that return a dict can be used with jsonrpc_view.
    
    """
    environ = request.environ

    length = request.content_length
    if length == 0:
        return HTTPLengthRequired()

    try:
        raw_body = environ['wsgi.input'].read(length)
        json_body = json.loads(urllib.unquote(raw_body))
    except ValueError:
        return jsonrpc_response(JSONRPC_PARSE_ERROR)

    rpc_id = json_body.get('id')
    rpc_params = json_body.get('params')
    rpc_method = json_body.get('method')
    rpc_version = json_body.get('jsonrpc')
    if rpc_version != JSONRPC_VERSION:
        return jsonrpc_response(JSONRPC_INVALID_REQUEST, rpc_id)

    view_callable = find_jsonrpc_view(request, rpc_method)
    log.debug('view callable %r found for method %r', view_callable, rpc_method)
    if not view_callable:
        return jsonrpc_response(JSONRPC_METHOD_NOT_FOUND, rpc_id)

    request.jsonrpc_params = rpc_params

    return jsonrpc_response(view_callable(request.context, request), rpc_id)
