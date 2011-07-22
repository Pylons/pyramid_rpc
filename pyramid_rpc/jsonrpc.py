import inspect
import logging

from pyramid.compat import json
from pyramid.interfaces import IViewMapperFactory, IViewMapper
from pyramid.response import Response
from zope.interface import implements, classProvides

from pyramid_rpc.api import view_lookup

__all__ = ['jsonrpc_endpoint']

log = logging.getLogger(__name__)

JSONRPC_VERSION = '2.0'

class JsonRpcError(Exception):
    code = None
    message = None

    def __init__(self, data=None):
        self.data = data

    def as_dict(self):
        """Return a dictionary representation of this object for
        serialization in a JSON-RPC response."""
        error = dict(code=self.code,
                     message=self.message)

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

    out = {
        'jsonrpc' : JSONRPC_VERSION,
        'id' : id,
        'result' : data,
    }
    try:
        body = json.dumps(out)
    except Exception:
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


class JsonRpcViewMapper(object):
    """
    Creating mapped view that map rpc arguments to view arguments.

    >>> @rpc_view(mapper=JsonRpcViewMapper)
    ... def say_hello(request, name):
    ...     return "Hello, %s" % name

    This is very limited support.
    
      - The view callable is assumed only function.
      - Don't use default values, arbitrary argument lists.
    """

    implements(IViewMapper)
    classProvides(IViewMapperFactory)

    def __init__(self, **info):
        self.info = info

    def __call__(self, view):
        def _mapped_callable(context, request):
            rpc_args = request.rpc_args
            args, varargs, keywords, defaults = inspect.getargspec(view)
            if isinstance(rpc_args, list):
                if len(args) != len(rpc_args) + 1: # for request
                    raise JsonRpcParamsInvalid
                return view(request, *rpc_args)
            elif isinstance(rpc_args, dict):
                if sorted(args[1:]) != sorted(rpc_args.keys()):
                    raise JsonRpcParamsInvalid
                return view(request, **rpc_args)
        return _mapped_callable


def jsonrpc_endpoint(request):
    """A base view to be used with add_route to setup a JSON-RPC dispatch
    endpoint
    
    Use this view with ``add_route`` to setup a JSON-RPC endpoint, for
    example::
        
        config.add_route('RPC2', '/apis/jsonrpc', view=jsonrpc_endpoint)
    
    JSON-RPC methods should then be registered with ``add_view`` using the
    route_name of the endpoint, the name as the jsonrpc method name. Or for
    brevity, the :class:`~pyramid_rpc.rpc_view` decorator can be used.
    
    For example, to register an jsonrpc method 'list_users'::
    
        @rpc_view()
        def list_users(request):
            json_params = request.rpc_args
            return {'users': [...]}
    
    Existing views that return a dict can be used with jsonrpc_view.
    
    """
    length = request.content_length
    if length == 0:
        return jsonrpc_error_response(JsonRpcRequestInvalid())

    try:
        body = json.loads(request.body)
    except ValueError:
        return jsonrpc_error_response(JsonRpcParseError())

    if isinstance(body, dict):
        rpc_id = body.get('id')
        if body.get('jsonrpc') != '2.0':
            return jsonrpc_error_response(JsonRpcRequestInvalid(), rpc_id)
        if 'method' not in body:
            return jsonrpc_error_response(JsonRpcRequestInvalid(), rpc_id)
        try:
            data = _call_rpc(request, body)
            return jsonrpc_response(data, rpc_id)
        except Exception, e:
            if rpc_id is None:
                return Response(content_type="text/plain")
            return jsonrpc_error_response(e, rpc_id)
    
    if isinstance(body, list):
        results = []
        for b in body:
            rpc_id = b.get('id')
            try:
                data = _call_rpc(request, b)
                if rpc_id is not None:
                    results.append(
                    {'jsonrpc': '2.0', 'result': data, 'id': rpc_id})
            except JsonRpcError, e:
                results.append({'error': e.as_dict(), 'id': rpc_id})
            except Exception, e:
                if rpc_id is not None:
                    e = JsonRpcInternalError(e)
                    results.append({'error': e.as_dict(), 'id': rpc_id})

        return Response(body=json.dumps(results),
                       content_type="application/json") 

    return jsonrpc_error_response(JsonRpcRequestInvalid())


def _call_rpc(request, body):
    rpc_args = body.get('params', [])
    rpc_method = body.get('method')
    rpc_version = body.get('jsonrpc')

    if rpc_version != JSONRPC_VERSION:
        raise JsonRpcRequestInvalid

    if not rpc_method:
        raise JsonRpcRequestInvalid

    view_callable = view_lookup(request, rpc_method)
    log.debug('view callable %r found for method %r', view_callable, rpc_method)
    if not view_callable:
        raise JsonRpcMethodNotFound

    request.rpc_args = rpc_args
    return view_callable(request.context, request)
