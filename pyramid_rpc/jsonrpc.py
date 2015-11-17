import json
import logging
import copy

import venusian
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import null_renderer
from pyramid.renderers import render
from pyramid.request import Request
from pyramid.response import Response
from pyramid.security import NO_PERMISSION_REQUIRED

from pyramid_rpc.compat import is_nonstr_iter
from pyramid_rpc.mapper import MapplyViewMapper
from pyramid_rpc.mapper import ViewMapperArgsInvalid
from pyramid_rpc.util import combine


log = logging.getLogger(__name__)

DEFAULT_RENDERER = 'pyramid_rpc:jsonrpc'

_marker = object()


class JsonRpcError(Exception):
    code = -32603 # sane default
    message = 'internal error' # sane default
    data = None

    def __init__(self, code=None, message=None, data=None):
        if code is not None:
            self.code = code
        if message is not None:
            self.message = message
        if data is not None:
            self.data = data

    def as_dict(self):
        """Return a dictionary representation of this object for
        serialization in a JSON-RPC response."""
        error = dict(code=self.code,
                     message=self.message)
        if self.data is not None:
            error['data'] = self.data
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


def make_error_response(request, error, id=None):
    """ Marshal a Python Exception into a ``Response`` object with a
    body that is a JSON string suitable for use as a JSON-RPC response
    with a content-type of ``application/json`` and return the response.

    """
    # we may need to render a parse error, at which point we don't know
    # much about the request
    renderer = getattr(request, 'rpc_renderer', DEFAULT_RENDERER)
    out = {
        'jsonrpc': '2.0',
        'id': id,
        'error': error.as_dict(),
    }
    body = render(renderer, out, request=request).encode('utf-8')

    response = Response(body, charset='utf-8')
    response.content_type = 'application/json'
    return response


def exception_view(exc, request):
    rpc_id = getattr(request, 'rpc_id', None)
    if isinstance(exc, JsonRpcError):
        fault = exc
        log.debug('json-rpc error rpc_id:%s "%s"',
                  rpc_id, exc.message)
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

    return make_error_response(request, fault, rpc_id)


def make_response(request, result):
    rpc_id = getattr(request, 'rpc_id', None)
    response = request.response

    # store content_type before render is called
    ct = response.content_type

    out = {
        'jsonrpc': '2.0',
        'id': rpc_id,
        'result': result,
    } if request.rpc_id is not None else ''
    response.body = render(
        request.rpc_renderer, out, request=request
    ).encode(response.charset)

    if ct == response.default_content_type:
        response.content_type = 'application/json'

    return response


def _render(value, system):
    return json.dumps(value)


def jsonrpc_renderer(info):
    return _render


class jsonrpc_view(object):
    """ Decorator that wraps a view and converts the result into a valid
    JSON-RPC Response object.

    """
    def __init__(self, renderer=DEFAULT_RENDERER):
        self.renderer = renderer

    def __call__(self, wrapped):
        def wrapper(context, request):
            request.rpc_renderer = self.renderer
            result = wrapped(context, request)
            if not request.is_response(result):
                result = make_response(request, result)
            return result
        return wrapper


def parse_request_GET(request):
    """ Parse JSON-RPC parameters from the request query string."""
    args = request.GET.get('params')
    if args is not None:
        try:
            request.rpc_args = json.loads(args)
        except ValueError:
            raise JsonRpcParseError
    else:
        request.rpc_args = ()

    request.rpc_method = request.GET.get('method')
    request.rpc_id = request.GET.get('id')
    request.rpc_version = request.GET.get('jsonrpc')


def parse_request_POST(request):
    """ Parse JSON-RPC parameters from the request body."""
    try:
        body = request.json_body
    except ValueError:
        raise JsonRpcParseError

    try:
        batched = body[:]
    except TypeError:
        batched = None

    if batched is not None:
        request.batched_rpc_requests = batched
    else:
        request.rpc_id = body.get('id')
        request.rpc_args = body.get('params', ())
        request.rpc_method = body.get('method')
        request.rpc_version = body.get('jsonrpc')


def setup_request(endpoint, request):
    """ Parse a JSON-RPC request body."""
    if request.method == 'GET':
        parse_request_GET(request)
    elif request.method == 'POST':
        parse_request_POST(request)
    else:
        log.debug('unsupported request method "%s"', request.method)
        raise JsonRpcRequestInvalid

    if hasattr(request, 'batched_rpc_requests'):
        log.debug('handling batched rpc request')
        # the checks below will look at the subrequests
        return

    if request.rpc_version != '2.0':
        log.debug('id:%s invalid rpc version %s',
                  request.rpc_id, request.rpc_version)
        raise JsonRpcRequestInvalid

    if request.rpc_method is None:
        log.debug('id:%s invalid rpc method', request.rpc_id)
        raise JsonRpcRequestInvalid

    log.debug('handling id:%s method:%s',
              request.rpc_id, request.rpc_method)


class EndpointPredicate(object):
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'jsonrpc endpoint = %s' % self.val

    phash = text

    def __call__(self, info, request):
        if self.val:
            # find the endpoint info
            key = info['route'].name
            endpoint = request.registry.jsonrpc_endpoints[key]

            # potentially setup either rpc v1 or v2 from the parsed body
            setup_request(endpoint, request)

            # update request with endpoint information
            request.rpc_endpoint = endpoint

            # Always return True so that even if it isn't a valid RPC it
            # will fall through to the notfound_view which will still
            # return a valid JSON-RPC response.
            return True


class MethodPredicate(object):
    def __init__(self, val, config):
        self.method = val

    def text(self):
        return 'jsonrpc method = %s' % self.method

    phash = text

    def __call__(self, context, request):
        return getattr(request, 'rpc_method', None) == self.method


class BatchedRequestPredicate(object):
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'jsonrpc batched request = %s' % self.val

    phash = text

    def __call__(self, context, request):
        if self.val:
            return hasattr(request, 'batched_rpc_requests')


def batched_request_view(request):
    json_response = []
    response = request.response
    for rpc_request in request.batched_rpc_requests:
        body = json.dumps(rpc_request).encode(request.charset)
        subrequest_headers = copy.copy(request.headers)
        subrequest_headers.pop('Content-Length', None)
        subrequest = Request.blank(path=request.path,
                                   environ=request.environ,
                                   base_url=request.application_url,
                                   headers=subrequest_headers,
                                   POST=body,
                                   charset=request.charset)
        subresponse = request.invoke_subrequest(subrequest, use_tweens=True)
        if subresponse.json_body != '':
            json_response.append(subresponse.json_body)
    if json_response:
        # use charset and content-type from last subresponse
        response.charset = subresponse.charset
        response.content_type = subresponse.content_type
        # will automatically be encoded
        response.json_body = json_response
    else:
        # if we would send an empty list, instead send nothing
        # per JSON-RPC: http://www.jsonrpc.org/specification#batch
        response.content_type = 'text/plain'
        response.body = b''
    return response


class Endpoint(object):
    def __init__(self, name, default_mapper, default_renderer):
        self.name = name
        self.default_mapper = default_mapper
        self.default_renderer = default_renderer


def add_jsonrpc_endpoint(config, name, *args, **kw):
    """Add an endpoint for handling JSON-RPC.

    ``name``

        The name of the endpoint.

    ``default_mapper``

        A default view mapper that will be passed as the ``mapper``
        argument to each of the endpoint's methods.

    ``default_renderer``

        A default renderer that will be passed as the ``renderer``
        argument to each of the endpoint's methods. This should be the
        string name of the renderer, registered via
        :meth:`pyramid.config.Configurator.add_renderer`.

    A JSON-RPC method also accepts all of the arguments supplied to
    :meth:`pyramid.config.Configurator.add_route`.

    """
    default_mapper = kw.pop('default_mapper', MapplyViewMapper)
    default_renderer = kw.pop('default_renderer', DEFAULT_RENDERER)

    endpoint = Endpoint(
        name,
        default_mapper=default_mapper,
        default_renderer=default_renderer,
    )

    config.registry.jsonrpc_endpoints[name] = endpoint

    kw['jsonrpc_endpoint'] = True
    config.add_route(name, *args, **kw)

    kw = {}
    kw['jsonrpc_batched'] = True
    kw['renderer'] = null_renderer
    config.add_view(batched_request_view, route_name=name,
                    permission=NO_PERMISSION_REQUIRED, **kw)
    config.add_view(exception_view, route_name=name, context=Exception,
                    permission=NO_PERMISSION_REQUIRED)


def add_jsonrpc_method(config, view, **kw):
    """Add a method to a JSON-RPC endpoint.

    ``endpoint``

        The name of the endpoint.

    ``method``

        The name of the method.

    A JSON-RPC method also accepts all of the arguments supplied to
    :meth:`pyramid.config.Configurator.add_view`.

    A view mapper is registered by default which will match the
    ``request.rpc_args`` to parameters on the view. To override this
    behavior simply set the ``mapper`` argument to None or another
    view mapper.

    .. note::

       An endpoint **must** be defined before methods may be added.

    """
    endpoint_name = kw.pop('endpoint', kw.pop('route_name', None))
    if endpoint_name is None:
        raise ConfigurationError(
            'Cannot register a JSON-RPC endpoint without specifying the '
            'name of the endpoint.')

    endpoint = config.registry.jsonrpc_endpoints.get(endpoint_name)
    if endpoint is None:
        raise ConfigurationError(
            'Could not find an endpoint with the name "%s".' % endpoint_name)

    # pop the method name
    method = kw.pop('method', None)
    if method is None:
        raise ConfigurationError(
            'Cannot register a JSON-RPC method without specifying the '
            '"method"')

    mapper = kw.pop('mapper', _marker)
    if mapper is _marker:
        # only override mapper if not supplied
        mapper = endpoint.default_mapper
    kw['mapper'] = mapper

    renderer = kw.pop('renderer', None)
    if renderer is None:
        renderer = endpoint.default_renderer
    kw['renderer'] = null_renderer

    kw['jsonrpc_method'] = method

    rpc_decorator = jsonrpc_view(renderer)
    decorator = kw.get('decorator', None)
    if decorator is None:
        decorator = rpc_decorator
    else:
        if not is_nonstr_iter(decorator):
            decorator = (decorator,)
        # we want to apply the view_wrapper first, then the other decorators
        # and combine() reverses the order, so ours goes last
        decorators = list(decorator) + [rpc_decorator]
        decorator = combine(*decorators)
    kw['decorator'] = decorator

    config.add_view(view, route_name=endpoint_name, **kw)


class jsonrpc_method(object):
    """This decorator may be used with pyramid view callables to enable
    them to respond to JSON-RPC method calls.

    If ``method`` is not supplied, then the callable name will be used
    for the method name.

    ``_depth`` may be specified when wrapping ``jsonrpc_method`` in another
    decorator. The value should reflect how many stack frames are between
    the wrapped target and ``jsonrpc_method``. Thus a decorator one level deep
    would pass in ``_depth=1``.

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
        depth = kw.pop('_depth', 0)

        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            config.add_jsonrpc_method(view=ob, **kw)

        info = venusian.attach(wrapped, callback, category='pyramid',
                               depth=depth + 1)
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
    if not hasattr(config.registry, 'jsonrpc_endpoints'):
        config.registry.jsonrpc_endpoints = {}

    config.add_view_predicate('jsonrpc_method', MethodPredicate)
    config.add_view_predicate('jsonrpc_batched', BatchedRequestPredicate)
    config.add_route_predicate('jsonrpc_endpoint', EndpointPredicate)

    config.add_renderer(DEFAULT_RENDERER, jsonrpc_renderer)
    config.add_directive('add_jsonrpc_endpoint', add_jsonrpc_endpoint)
    config.add_directive('add_jsonrpc_method', add_jsonrpc_method)
    config.add_view(exception_view, context=JsonRpcError,
                    permission=NO_PERMISSION_REQUIRED)
