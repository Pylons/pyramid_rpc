import inspect

from pyramid.interfaces import IViewMapperFactory

from zope.interface import implementer

from pyramid_rpc.compat import PY3

if PY3: # pragma: no cover
    def _inspect_ob(f):
        im = False

        if hasattr(f, '__func__'):
            im = True

        elif not hasattr(f, '__defaults__'):
            if hasattr(f, '__call__'):
                f = f.__call__
                if hasattr(f, '__func__'):
                    im = True

        if im:
            f = f.__func__
            c = f.__code__
            defaults = f.__defaults__
            names = c.co_varnames[1:c.co_argcount]
        else:
            c = f.__code__
            defaults = f.__defaults__
            names = c.co_varnames[:c.co_argcount]

        return names, defaults
else:
    def _inspect_ob(f):
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
            c = f.func_code
            defaults = f.func_defaults
            names = c.co_varnames[:c.co_argcount]

        return names, defaults

@implementer(IViewMapperFactory)
class MapplyViewMapper(object):

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
        names, defaults = _inspect_ob(ob)

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
