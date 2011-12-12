import logging

import xmlrpclib

from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.view import view_config

from zope.deprecation import deprecated

from pyramid_rpc.api import view_lookup
from pyramid_rpc.api import MapplyViewMapper
from pyramid_rpc.api import ViewMapperArgsInvalid


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


def xmlrpc_marshal(data):
    """ Marshal a Python data structure into an XML document suitable
    for use as an XML-RPC response and return the document.  If
    ``data`` is an ``xmlrpclib.Fault`` instance, it will be marshalled
    into a suitable XML-RPC fault response."""
    if isinstance(data, xmlrpclib.Fault):
        return xmlrpclib.dumps(data)
    else:
        return xmlrpclib.dumps((data,),  methodresponse=True)


def parse_xmlrpc_request(request):
    """ Deserialize the body of a request from an XML-RPC request
    document into a set of params and return a two-tuple.  The first
    element in the tuple is the method params as a sequence, the
    second element in the tuple is the method name."""
    if request.content_length > (1 << 23):
        # protect from DOS (> 8MB body)
        raise ValueError('Body too large (%s bytes)' % request.content_length)
    params, method = xmlrpclib.loads(request.body)
    return params, method


class xmlrpc_view(object):
    """ This decorator may be used with pyramid view callables to enable them
    to repsond to XML-RPC method calls.

    If ``method`` is not supplied, then the callable name will be used for
    the method name. If ``route_name`` is not supplied, it is assumed that
    the appropriate route was added to the application's config (named
    'RPC2').

    """
    def __init__(self, method=None, route_name='RPC2'):
        self.method = method
        self.route_name = route_name

    def __call__(self, wrapped, view_config=view_config):
        # view_config passable for unit testing purposes only
        method_name = self.method or wrapped.__name__
        try:
            # pyramid 1.1
            from pyramid.renderers import null_renderer
            renderer = null_renderer
        except ImportError:  # pragma: no cover
            # pyramid 1.0
            renderer = None
        return view_config(route_name=self.route_name, name=method_name,
                           renderer=renderer)(wrapped)


def xmlrpc_endpoint(request):
    """A base view to be used with add_route to setup an XML-RPC dispatch
    endpoint

    Use this view with ``add_route`` to setup an XML-RPC endpoint, for
    example::

        config.add_route('RPC2', '/apis/RPC2', view=xmlrpc_endpoint)

    XML-RPC methods should then be registered with ``add_view`` using the
    route_name of the endpoint, the name as the xmlrpc method name. Or for
    brevity, the :class:`~pyramid_rpc.xmlrpc.xmlrpc_view` decorator can be
    used.

    For example, to register an xmlrpc method 'list_users'::

        @xmlrpc_view()
        def list_users(request):
            args = request.rpc_args
            return {'users': [...]}

    Existing views that return a dict can be used with xmlrpc_view.

    """
    params, method = parse_xmlrpc_request(request)
    request.rpc_args = request.xmlrpc_args = params  # b/w compat xmlrpc_args

    view_callable = view_lookup(request, method=method)
    if not view_callable:
        return HTTPNotFound("No method of that name was found.")
    else:
        data = view_callable(request.context, request)
        xml = xmlrpc_marshal(data)
        response = Response(xml)
        response.content_type = 'text/xml'
        response.content_length = len(xml)
        return response

deprecated('xmlrpc_endpoint',
           ('Deprecated as of pyramid_rpc 0.3, use the new API as described '
            'in the documentation.'))


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
    self.add_view(exception_view, route_name=name, context=Exception)


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
        endpoint = kw.pop('endpoint', kw.pop('route_name', None))
        if endpoint is None:
            raise ConfigurationError(
                'Cannot register a XML-RPC endpoint without specifying the '
                'name of the endpoint.')

        kw.setdefault('mapper', MapplyViewMapper)
        kw.setdefault('renderer', 'pyramid_rpc:xmlrpc')
        kw['route_name'] = endpoint
        self.method = method
        self.kw = kw

    def __call__(self, wrapped):
        method = self.method or wrapped.__name__
        kw = self.kw.copy()

        def xmlrpc_method_predicate(context, request):
            return getattr(request, 'rpc_method', None) == method
        predicates = kw.setdefault('custom_predicates', [])
        predicates.append(xmlrpc_method_predicate)
        return view_config(**kw)(wrapped)


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
    config.add_view(exception_view, context=xmlrpclib.Fault)
