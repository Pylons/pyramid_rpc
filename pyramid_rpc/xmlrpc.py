import xmlrpclib
from pyramid.response import Response

from pyramid.interfaces import IRequest
from pyramid.interfaces import IRouteRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier

from pyramid.exceptions import NotFound


def xmlrpc_marshal(data):
    """ Marshal a Python data structure into an XML document suitable
    for use as an XML-RPC response and return the document.  If
    ``data`` is an ``xmlrpclib.Fault`` instance, it will be marshalled
    into a suitable XML-RPC fault response."""
    if isinstance(data, xmlrpclib.Fault):
        return xmlrpclib.dumps(data)
    else:
        return xmlrpclib.dumps((data,),  methodresponse=True)

def xmlrpc_response(data):
    """ Marshal a Python data structure into a webob ``Response``
    object with a body that is an XML document suitable for use as an
    XML-RPC response with a content-type of ``text/xml`` and return
    the response."""
    xml = xmlrpc_marshal(data)
    response = Response(xml)
    response.content_type = 'text/xml'
    response.content_length = len(xml)
    return response

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

def xmlrpc_view(wrapped):
    """ This decorator turns functions which accept params and return Python
    structures into functions suitable for use as Pyramid views that speak
    XML-RPC.  The decorated function must accept a ``context`` argument and
    zero or more positional arguments (conventionally named ``*params``).

    E.g.::

      from pyramid_xmlrpc import xmlrpc_view

      @xmlrpc_view
      def say(context, what):
          if what == 'hello'
              return {'say':'Hello!'}
          else:
              return {'say':'Goodbye!'}

    Equates to::

      from pyramid_xmlrpc import parse_xmlrpc_request
      from pyramid_xmlrpc import xmlrpc_response

      def say_view(context, request):
          params, method = parse_xmlrpc_request(request)
          return say(context, *params)

      def say(context, what):
          if what == 'hello'
              return {'say':'Hello!'}
          else:
              return {'say':'Goodbye!'}

    Note that if you use :class:`~pyramid.view.view_config`, you must
    decorate your view function in the following order for it to be
    recognized by the convention machinery as a view::

      from pyramid.view import view_config
      from pyramid_xmlrpc import xmlrpc_view

      @view_config(name='say')
      @xmlrpc_view
      def say(context, what):
          if what == 'hello'
              return {'say':'Hello!'}
          else:
              return {'say':'Goodbye!'}

    In other words do *not* decorate it in :func:`~pyramid_xmlrpc.xmlrpc_view`,
    then :class:`~pyramid.view.view_config`; it won't work.
    """
    
    def _curried(context, request):
        params, method = parse_xmlrpc_request(request)
        value = wrapped(context, *params)
        return xmlrpc_response(value)
    _curried.__name__ = wrapped.__name__
    _curried.__grok_module__ = wrapped.__module__ 

    return _curried
    
class XMLRPCView:
    """A base class for a view that serves multiple methods by XML-RPC.

    Subclass and add your methods as described in the documentation.
    """

    def __init__(self,context,request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        This method de-serializes the XML-RPC request and
        dispatches the resulting method call to the correct
        method on the :class:`~pyramid_xmlrpc.XMLRPCView`
        subclass instance.

        .. warning::
          Do not override this method in any subclass if you
          want XML-RPC to continute to work!
          
        """
        params, method = parse_xmlrpc_request(self.request)
        return xmlrpc_response(getattr(self,method)(*params))

def xmlrpc_endpoint(request):
    """A base view to be used with add_route to setup an XML-RPC dispatch
    endpoint
    
    Use this view with ``add_route`` to setup an XML-RPC endpoint, for
    example::
        
        config.add_route('RPC2', '/apis/RPC2', view=xmlrpc_endpoint)
    
    XML-RPC methods should then be registered with ``add_view`` using the
    route_name of the endpoint, the name as the xmlrpc method name, and
    renderer of 'xmlrpc'. Or for brevity, the xmlrpc decorator can be used.
    
    For example, to register an xmlrpc method 'list_users'::
    
        @xmlrpc()
        def list_users(request):
            xml_args = request.xmlrpc_args
            return {'users': [...]}
    
    Existing views that return a dict can be used with xmlrpc_view.
    
    """
    registry = request.registry
    params, method = parse_xmlrpc_request(request)
    request.xmlrpc_args = params
    request_iface = registry.queryUtility(
        IRouteRequest, name=request.route.name,
        default=IRequest)
    context_iface = providedBy(request.context)
    view_callable = adapters.lookup(
        (IViewClassifier, request_iface, context_iface),
        IView, name=method, default=None)
    if not view_callable:
        return NotFound("No method of that name was found.")
    else:
        return view_callable(context, request)
