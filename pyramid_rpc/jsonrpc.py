import logging

import venusian
from pyramid.compat import json
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response

from pyramid_rpc.api import MapplyViewMapper
from pyramid_rpc.api import ViewMapperArgsInvalid


log = logging.getLogger(__name__)


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


def jsonrpc_error_response(error, id=None):
    """ Marshal a Python Exception into a webob ``Response``
    object with a body that is a JSON string suitable for use as
    a JSON-RPC response with a content-type of ``application/json``
    and return the response."""

    body = json.dumps({
        'jsonrpc': '2.0',
        'id': id,
        'error': error.as_dict(),
    })

    response = Response(body)
    response.content_type = 'application/json'
    response.content_length = len(body)
    return response


def exception_view(exc, request):
    rpc_id = getattr(request, 'rpc_id', None)
    if isinstance(exc, JsonRpcError):
        fault = exc
    elif isinstance(exc, HTTPNotFound):
        fault = JsonRpcMethodNotFound()
        log.debug('json-rpc method not found rpc_id:%s "%s"',
                  rpc_id, request.rpc_method)
    elif isinstance(exc, HTTPForbidden):
        fault = JsonRpcRequestInvalid()
        log.debug('json-rpc method forbidden rpc_id:%s "%s"',
                  rpc_id, request.rpc_method)
    elif isinstance(exc, ViewMapperArgsInvalid):
        fault = JsonRpcParamsInvalid()
        log.debug('json-rpc invalid method params')
    else:
        fault = JsonRpcInternalError()
        log.exception('json-rpc exception rpc_id:%s "%s"', rpc_id, exc)

    return jsonrpc_error_response(fault, rpc_id)


def jsonrpc_renderer(info):
    def _render(value, system):
        request = system.get('request')
        if request is not None:
            rpc_id = getattr(request, 'rpc_id', None)
            response = request.response

            if rpc_id is None:
                response.status = 204
                del response.content_type
                return ''

            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'application/json'

            out = {
                'jsonrpc': '2.0',
                'id': rpc_id,
                'result': value,
            }
            return json.dumps(out)
    return _render


def setup_jsonrpc(request):
    try:
        body = request.json_body
    except ValueError:
        raise JsonRpcParseError

    request.rpc_id = body.get('id')
    request.rpc_args = body.get('params', ())
    request.rpc_method = body.get('method')
    request.rpc_version = body.get('jsonrpc')

    if request.rpc_version != '2.0':
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
    self.add_view(exception_view, route_name=name, context=Exception)


def add_jsonrpc_method(self, view, **kw):
    """Add a method to a JSON-RPC endpoint.

    endpoint

        The name of the endpoint.

    method

        The name of the method.

    A JSON-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_view`` method.

    A view mapper is registered by default which will match the
    ``request.rpc_args`` to parameters on the view. To override this
    behavior simply set the ``mapper`` argument to None or another
    view mapper.

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
    kw.setdefault('mapper', MapplyViewMapper)
    kw.setdefault('renderer', 'pyramid_rpc:jsonrpc')
    self.add_view(view, route_name=endpoint, **kw)


class jsonrpc_method(object):
    """This decorator may be used with pyramid view callables to enable
    them to respond to JSON-RPC method calls.

    If ``method`` is not supplied, then the callable name will be used
    for the method name.

    This is the lazy analog to the
    :func:`~pyramid_rpc.jsonrpc.add_jsonrpc_method`` and accepts all of
    the same arguments.

    """
    def __init__(self, method=None, **kw):
        self.method = method
        self.kw = kw

    def __call__(self, wrapped):
        kw = self.kw.copy()
        kw['method'] = self.method or wrapped.__name__

        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            config.add_jsonrpc_method(view=ob, **kw)

        info = venusian.attach(wrapped, callback, category='pyramid')
        if info.scope == 'class':
            # ensure that attr is set if decorating a class method
            kw.setdefault('attr', wrapped.__name__)

        kw['_info'] = info.codeinfo  # fbo action_method
        return wrapped


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
