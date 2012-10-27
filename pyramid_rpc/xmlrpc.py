import logging

import venusian
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.security import NO_PERMISSION_REQUIRED

from pyramid_rpc.api import MapplyViewMapper
from pyramid_rpc.api import ViewMapperArgsInvalid
from pyramid_rpc.compat import xmlrpclib


log = logging.getLogger(__name__)


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

    xml = xmlrpclib.dumps(fault)
    response = Response(xml)
    response.content_type = 'text/xml'
    response.content_length = len(xml)
    return response


def xmlrpc_renderer(info):
    def _render(value, system):
        request = system.get('request')
        if request is not None:
            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'text/xml'

            return xmlrpclib.dumps((value,), methodresponse=True)
    return _render


def setup_xmlrpc(request):
    try:
        params, method = xmlrpclib.loads(request.body)
    except Exception:
        raise XmlRpcParseError

    request.rpc_args = params
    request.rpc_method = method

    if method is None:
        raise XmlRpcMethodNotFound


def add_xmlrpc_endpoint(self, name, *args, **kw):
    """Add an endpoint for handling XML-RPC.

    name

        The name of the endpoint.

    A XML-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_route`` method.

    """
    def xmlrpc_endpoint_predicate(info, request):
        # potentially setup either rpc v1 or v2 from the parsed body
        setup_xmlrpc(request)

        # Always return True so that even if it isn't a valid RPC it
        # will fall through to the notfound_view which will still
        # return a valid XML-RPC response.
        return True
    predicates = kw.setdefault('custom_predicates', [])
    predicates.append(xmlrpc_endpoint_predicate)
    self.add_route(name, *args, **kw)
    self.add_view(exception_view, route_name=name, context=Exception,
                  permission=NO_PERMISSION_REQUIRED)


def add_xmlrpc_method(self, view, **kw):
    """Add a method to a XML-RPC endpoint.

    endpoint

        The name of the endpoint.

    method

        The name of the method.

    A XML-RPC method also accepts all of the arguments supplied to
    Pyramid's ``add_view`` method.

    A view mapper is registered by default which will match the
    ``request.rpc_args`` to parameters on the view. To override this
    behavior simply set the ``mapper`` argument to None or another
    view mapper.

    """
    endpoint = kw.pop('endpoint', kw.pop('route_name', None))
    if endpoint is None:
        raise ConfigurationError(
            'Cannot register a XML-RPC endpoint without specifying the '
            'name of the endpoint.')

    method = kw.pop('method', None)
    if method is None:
        raise ConfigurationError(
            'Cannot register a XML-RPC method without specifying the '
            '"method"')

    def xmlrpc_method_predicate(context, request):
        return getattr(request, 'rpc_method', None) == method
    predicates = kw.setdefault('custom_predicates', [])
    predicates.append(xmlrpc_method_predicate)
    kw.setdefault('mapper', MapplyViewMapper)
    kw.setdefault('renderer', 'pyramid_rpc:xmlrpc')
    self.add_view(view, route_name=endpoint, **kw)


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
    config.add_directive('add_xmlrpc_endpoint', add_xmlrpc_endpoint)
    config.add_directive('add_xmlrpc_method', add_xmlrpc_method)
    config.add_renderer('pyramid_rpc:xmlrpc', xmlrpc_renderer)
    config.add_view(exception_view, context=xmlrpclib.Fault,
                    permission=NO_PERMISSION_REQUIRED)
