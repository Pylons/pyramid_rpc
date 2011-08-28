import inspect
import logging

import venusian
from pyramid.compat import json
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPNoContent
from pyramid.httpexceptions import HTTPNotFound
from pyramid.interfaces import IViewMapperFactory, IViewMapper
from pyramid.response import Response
from pyramid.view import view_config

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


def exception_view(exc, request):
    rpc_id = getattr(request, 'rpc_id', None)
    return jsonrpc_error_response(exc, rpc_id)


def notfound_view(exc, request):
    rpc_id = getattr(request, 'rpc_id', None)
    return jsonrpc_error_response(JsonRpcMethodNotFound(), rpc_id)


def notification_view(exc, request):
    return exc


def jsonrpc_renderer(info):
    def _render(value, system):
        request = system.get('request')
        if request is not None:
            rpc_id = getattr(request, 'rpc_id', None)
            if rpc_id is None:
                raise HTTPNoContent()

            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'application/json'

            out = {
                'jsonrpc' : JSONRPC_VERSION,
                'id' : rpc_id,
                'result' : value,
            }
            return json.dumps(out)
    return _render


def setup_jsonrpc(request):
    try:
        body = request.json_body
    except ValueError:
        raise JsonRpcParseError

    request.rpc_id = body.get('id')
    request.rpc_args = body.get('params', [])
    request.rpc_method = body.get('method')
    request.rpc_version = body.get('jsonrpc')

    if request.rpc_version != JSONRPC_VERSION:
        raise JsonRpcRequestInvalid

    if request.rpc_method is None:
        raise JsonRpcRequestInvalid


def add_jsonrpc_endpoint(self, name, *args, **kw):
    """Add an endpoint for handling JSON-RPC.

    name

        The name of the endpoint.

    A JSON-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_route`` method.

    """
    def jsonrpc_endpoint_predicate(info, request):
        # potentially setup either rpc v1 or v2 from the parsed body
        setup_jsonrpc(request)

        # Always return True so that even if it isn't a valid RPC it
        # will fall through to the notfound_view which will still
        # return a valid JSON-RPC response.
        return True
    predicates = kw.setdefault('custom_predicates', [])
    predicates.append(jsonrpc_endpoint_predicate)
    self.add_route(name, *args, **kw)
    self.add_view(notfound_view, route_name=name, context=HTTPNotFound)
    self.add_view(notification_view, route_name=name, context=HTTPNoContent)
    self.add_view(exception_view, route_name=name, context=Exception)


def add_jsonrpc_method(self, view, **kw):
    """Add a method to a JSON-RPC endpoint.

    endpoint

        The name of the endpoint.

    method

        The name of the method.

    A JSON-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_view`` method.

    """
    endpoint = kw.pop('endpoint', kw.pop('route_name', None))
    if endpoint is None:
        raise ConfigurationError(
            'Cannot register a JSON-RPC endpoint without specifying the '
            'name of the endpoint.')

    method = kw.pop('method', None)
    if method is None:
        raise ConfigurationError(
            'Cannot register a JSON-RPC method without specifying the '
            '"method"')

    def jsonrpc_method_predicate(context, request):
        return getattr(request, 'rpc_method', None) == method
    predicates = kw.setdefault('custom_predicates', [])
    predicates.append(jsonrpc_method_predicate)
    kw.setdefault('renderer', 'pyramid_rpc:jsonrpc')
    self.add_view(view, route_name=endpoint, **kw)


class jsonrpc_method(object):
    """This decorator may be used with pyramid view callables to enable
    them to respond to JSON-RPC method calls.

    If ``method`` is not supplied, then the callable name will be used
    for the method name.

    The decorator is lazy analog to ``config.add_jsonrpc_method`` and
    accepts all of the same arguments.

    """
    venusian = venusian # for testing injection
    def __init__(self, method=None, **kw):
        endpoint = kw.pop('endpoint', kw.pop('route_name', None))
        if endpoint is None:
            raise ConfigurationError(
                'Cannot register a JSON-RPC endpoint without specifying the '
                'name of the endpoint.')

        kw.setdefault('renderer', 'pyramid_rpc:jsonrpc')
        kw['route_name'] = endpoint
        self.method = method
        self.kw = kw

    def __call__(self, wrapped):
        view_config.venusian = self.venusian
        method = self.method or wrapped.__name__
        kw = self.kw.copy()
        def jsonrpc_method_predicate(context, request):
            return getattr(request, 'rpc_method', None) == method
        predicates = kw.setdefault('custom_predicates', [])
        predicates.append(jsonrpc_method_predicate)
        return view_config(**kw)(wrapped)


def includeme(config):
    """ Set up standard configurator registrations.  Use via:

    .. code-block:: python

       config = Configurator()
       config.include('pyramid_rpc.jsonrpc')

    Once this function has been invoked, two new directives will be
    available on the configurator:

    - ``add_jsonrpc_endpoint``: Add an endpoint for handling JSON-RPC.

    - ``add_jsonrpc_method``: Add a method to a JSON-RPC endpoint.

    """
    config.add_directive('add_jsonrpc_endpoint', add_jsonrpc_endpoint)
    config.add_directive('add_jsonrpc_method', add_jsonrpc_method)
    config.add_renderer('pyramid_rpc:jsonrpc', jsonrpc_renderer)
    config.add_view(exception_view, context=JsonRpcError)

