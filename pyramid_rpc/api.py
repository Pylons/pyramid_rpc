"""RPC Utility methods

These utility methods are intended for use by RPC functions to lookup
qualifying view to call in response to an RPC method.

"""
from zope.interface import providedBy

from pyramid.exceptions import NotFound
from pyramid.interfaces import IRequest
from pyramid.interfaces import IRouteRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier


def view_lookup(request, method):
    """Lookup and return a view based on the request, context, and
    method name
    
    This function will use the current routes name to locate the
    view using Pyramid's view lookup machinery.

    """
    registry = request.registry
    adapters = registry.adapters
    
    # Hairy view lookup stuff below, woo!
    request_iface = registry.queryUtility(
        IRouteRequest, name=request.matched_route.name,
        default=IRequest)
    context_iface = providedBy(request.context)
    view_callable = adapters.lookup(
        (IViewClassifier, request_iface, context_iface),
        IView, name=method, default=None)
    return view_callable
