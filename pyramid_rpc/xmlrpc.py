import logging

import venusian
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import null_renderer
from pyramid.response import Response
from pyramid.security import NO_PERMISSION_REQUIRED

from .compat import (
    PY3,
    is_nonstr_iter,
    text_type,
    xmlrpclib,
)
from .mapper import MapplyViewMapper
from .mapper import ViewMapperArgsInvalid
from .util import combine


log = logging.getLogger(__name__)


_marker = object()


class XmlRpcError(xmlrpclib.Fault):
    faultCode = None
    faultString = None

    def __init__(self):
        xmlrpclib.Fault.__init__(self, self.faultCode, self.faultString)


class XmlRpcApplicationError(XmlRpcError):
    faultCode = -32500
    faultString = 'application error'


class XmlRpcMethodNotFound(XmlRpcError):
    faultCode = -32601
    faultString = 'server error; requested method not found'


class XmlRpcInvalidMethodParams(XmlRpcError):
    faultCode = -32602
    faultString = 'server error; invalid method params'


class XmlRpcParseError(XmlRpcError):
    faultCode = -32700
    faultString = 'parse error; not well formed'


def exception_view(exc, request):
    if isinstance(exc, xmlrpclib.Fault):
        fault = exc
    elif isinstance(exc, HTTPNotFound):
        fault = XmlRpcMethodNotFound()
        log.debug('xml-rpc method not found "%s"', request.rpc_method)
    elif isinstance(exc, ViewMapperArgsInvalid):
        fault = XmlRpcInvalidMethodParams()
        log.debug('xml-rpc method not found "%s"', request.rpc_method)
    else:
        fault = XmlRpcApplicationError()
        log.exception('xml-rpc exception "%s"', exc)

    xml = xmlrpclib.dumps(fault, methodresponse=True)
    response = Response(content_type='text/xml')
    _set_response_body(response, xml)
    return response


if PY3: # pragma: no cover
    def _set_response_body(response, result):
        response.text = result
else:
    def _set_response_body(response, result):
        response.body = result


def make_response(request, result):
    response = request.response

    ct = response.content_type
    if ct == response.default_content_type:
        response.content_type = 'text/xml'

    xml = xmlrpclib.dumps((result,), methodresponse=True)
    _set_response_body(response, xml)
    return response


class xmlrpc_view(object):
    """ Decorator that wraps a view and converts the result into a valid
    JSON-RPC Response object.

    """
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __call__(self, context, request):
        result = self.wrapped(context, request)
        if not request.is_response(result):
            result = make_response(request, result)
        return result


class EndpointPredicate(object):
    def __call__(self, info, request):
        # find the endpoint info
        key = info['route'].name
        endpoint = request.registry.rpc_endpoints[key]

        # parse the request body
        setup_request(endpoint, request)

        # update request with endpoint information
        request.rpc_endpoint = endpoint

        # Always return True so that even if it isn't a valid RPC it
        # will fall through to the notfound_view which will still
        # return a valid XML-RPC response.
        return True


class MethodPredicate(object):
    def __init__(self, method):
        self.method = method

    def __call__(self, context, request):
        return getattr(request, 'rpc_method') == self.method


class Endpoint(object):
    def __init__(self, name, default_mapper):
        self.name = name
        self.default_mapper = default_mapper


def setup_request(endpoint, request):
    try:
        params, method = xmlrpclib.loads(request.body)
    except Exception:
        raise XmlRpcParseError

    request.rpc_args = params
    request.rpc_method = method

    if method is None:
        raise XmlRpcMethodNotFound


def add_xmlrpc_endpoint(config, name, *args, **kw):
    """Add an endpoint for handling XML-RPC.

    ``name``

        The name of the endpoint.

    ``default_mapper``

        A default view mapper that will be passed as the ``mapper``
        argument to each of the endpoint's methods.

    A XML-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_route`` method.

    """
    default_mapper = kw.pop('default_mapper', MapplyViewMapper)

    endpoint = Endpoint(
        name,
        default_mapper=default_mapper,
    )

    config.registry.rpc_endpoints[name] = endpoint

    predicates = kw.setdefault('custom_predicates', [])
    predicates.append(EndpointPredicate())

    config.add_route(name, *args, **kw)
    config.add_view(exception_view, route_name=name, context=Exception,
                  permission=NO_PERMISSION_REQUIRED)


def add_xmlrpc_method(config, view, **kw):
    """Add a method to a XML-RPC endpoint.

    ``endpoint``

        The name of the endpoint.

    ``method``

        The name of the method.

    A XML-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_view`` method.

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
            'Cannot register a XML-RPC endpoint without specifying the '
            'name of the endpoint.')

    endpoint = config.registry.rpc_endpoints.get(endpoint_name)
    if endpoint is None:
        raise ConfigurationError(
            'Could not find an endpoint with the name "%s".' % endpoint_name)

    method = kw.pop('method', None)
    if method is None:
        raise ConfigurationError(
            'Cannot register a XML-RPC method without specifying the '
            '"method"')

    mapper = kw.pop('mapper', _marker)
    if mapper is _marker:
        # only override mapper if not supplied
        mapper = endpoint.default_mapper
    kw['mapper'] = mapper

    decorator = kw.get('decorator', None)
    if decorator is None:
        decorator = xmlrpc_view
    else:
        if not is_nonstr_iter(decorator):
            decorator = (decorator,)
        # we want to apply the view_wrapper first, then the other decorators
        # and combine() reverses the order, so ours goes last
        decorators = list(decorator) + [xmlrpc_view]
        decorator = combine(*decorators)
    kw['decorator'] = decorator

    predicates = kw.setdefault('custom_predicates', [])
    predicates.append(MethodPredicate(method))

    kw['renderer'] = null_renderer
    config.add_view(view, route_name=endpoint_name, **kw)


class xmlrpc_method(object):
    """This decorator may be used with pyramid view callables to enable
    them to respond to XML-RPC method calls.

    If ``method`` is not supplied, then the callable name will be used
    for the method name.

    This is the lazy analog to the
    :func:`~pyramid_rpc.xmlrpc.add_xmlrpc_method`` and accepts all of
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
            config.add_xmlrpc_method(view=ob, **kw)

        info = venusian.attach(wrapped, callback, category='pyramid')
        if info.scope == 'class':
            # ensure that attr is set if decorating a class method
            kw.setdefault('attr', wrapped.__name__)

        kw['_info'] = info.codeinfo # fbo action_method
        return wrapped


def includeme(config):
    """ Set up standard configurator registrations.  Use via:

    .. code-block:: python

       config = Configurator()
       config.include('pyramid_rpc.xmlrpc')

    Once this function has been invoked, two new directives will be
    available on the configurator:

    - ``add_xmlrpc_endpoint``: Add an endpoint for handling XML-RPC.

    - ``add_xmlrpc_method``: Add a method to a XML-RPC endpoint.

    """
    if not hasattr(config.registry, 'rpc_endpoints'):
        config.registry.rpc_endpoints = {}

    config.add_directive('add_xmlrpc_endpoint', add_xmlrpc_endpoint)
    config.add_directive('add_xmlrpc_method', add_xmlrpc_method)
    config.add_view(exception_view, context=xmlrpclib.Fault,
                    permission=NO_PERMISSION_REQUIRED)
