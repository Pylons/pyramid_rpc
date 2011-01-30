import xmlrpclib

import venusian

from pyramid.exceptions import NotFound
from pyramid.response import Response
from pyramid.view import view_config

from pyramid_rpc.api import view_lookup


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
    venusian = venusian # for testing injection
    def __init__(self, method=None, route_name='RPC2'):
        self.method = method
        self.route_name = route_name

    def __call__(self, wrapped):
        view_config.venusian = self.venusian
        method_name = self.method or wrapped.__name__
        return view_config(route_name=self.route_name, name=method_name)(wrapped)


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
            xml_args = request.xmlrpc_args
            return {'users': [...]}
    
    Existing views that return a dict can be used with xmlrpc_view.
    
    """
    params, method = parse_xmlrpc_request(request)
    request.rpc_args = request.xmlrpc_args = params # b/w compat xmlrpc_args
    
    view_callable = view_lookup(request, method=method)
    if not view_callable:
        return NotFound("No method of that name was found.")
    else:
        data = view_callable(request.context, request)
        xml = xmlrpc_marshal(data)
        response = Response(xml)
        response.content_type = 'text/xml'
        response.content_length = len(xml)
        return response
