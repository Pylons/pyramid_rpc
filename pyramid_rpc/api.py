"""RPC Utility methods

These utility methods are intended for use by RPC functions to lookup
qualifying view to call in response to an RPC method.

"""
import inspect

from pyramid.interfaces import IRequest
from pyramid.interfaces import IRouteRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.interfaces import IViewMapperFactory

from zope.interface import implements
from zope.interface import providedBy


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


class MapplyViewMapper(object):
    implements(IViewMapperFactory)

    def __init__(self, **kw):
        self.attr = kw.get('attr')

    def __call__(self, view):
        attr = self.attr
        if inspect.isclass(view):
            def _class_view(context, request):
                params = getattr(request, 'rpc_args', ())
                keywords = dict(request.params.items())
                if request.matchdict:
                    keywords.update(request.matchdict)
                if isinstance(params, dict):
                    keywords.update(params)
                    params = tuple()
                else:
                    params = tuple(params)
                if attr is None:
                    inst = view(request)
                    response = self.mapply(inst, params, keywords)
                else:
                    inst = view(request)
                    response = self.mapply(getattr(inst, attr), params,
                                           keywords)
                request.__view__ = inst
                return response
            mapped_view = _class_view
        else:
            def _nonclass_view(context, request):
                params = getattr(request, 'rpc_args', ())
                keywords = dict(request.params.items())
                if request.matchdict:
                    keywords.update(request.matchdict)
                if isinstance(params, dict):
                    keywords.update(params)
                    params = (request,)
                else:
                    params = (request,) + tuple(params)
                if attr is None:
                    response = self.mapply(view, params, keywords)
                else:
                    response = self.mapply(getattr(view, attr), params,
                                           keywords)
                return response
            mapped_view = _nonclass_view

        return mapped_view

    def mapply(self, ob, positional, keyword):

        f = ob
        im = False

        if hasattr(f, 'im_func'):
            im = True

        elif not hasattr(f, 'func_defaults'):
            if hasattr(f, '__call__'):
                f = f.__call__
                if hasattr(f, 'im_func'):
                    im = True

        if im:
            f = f.im_func
            c = f.func_code
            defaults = f.func_defaults
            names = c.co_varnames[1:c.co_argcount]
        else:
            defaults = f.func_defaults
            c = f.func_code
            names = c.co_varnames[:c.co_argcount]

        nargs = len(names)
        args = []
        if positional:
            positional = list(positional)
            if len(positional) > nargs:
                raise ViewMapperArgsInvalid('too many arguments')
            args = positional

        get = keyword.get
        nrequired = len(names) - (len(defaults or ()))
        for index in range(len(args), len(names)):
            name = names[index]
            v = get(name, args)
            if v is args:
                if index < nrequired:
                    raise ViewMapperArgsInvalid(
                        'argument %s was omitted' % name)
                else:
                    v = defaults[index - nrequired]
            args.append(v)

        args = tuple(args)
        return ob(*args)


class ViewMapperArgsInvalid(TypeError):
    pass
