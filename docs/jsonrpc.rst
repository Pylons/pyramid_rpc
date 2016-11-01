.. _jsonrpc:

========
JSON-RPC 
========

:mod:`pyramid_rpc` supports 
`JSON-RPC 2.0 Specification <http://www.jsonrpc.org/specification>`_ .

.. code-block:: python

    from pyramid.config import Configurator
    from pyramid_rpc.jsonrpc import jsonrpc_method

    @jsonrpc_method(endpoint='api')
    def say_hello(request, name):
        return 'hello, %s!' % name

    def main(global_conf, **settings):
        config = Configurator(settings=settings)
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('api', '/api')
        config.scan(__name__)
        return config.make_wsgi_app()

    if __name__ == '__main__':
        from wsgiref.simple_server import make_server
        app = main({})
        server = make_server('', 8080, app)
        server.serve_forever()

Setup
=====

Use the ``includeme`` via :meth:`pyramid.config.Configurator.include`:

.. code-block:: python

    config.include('pyramid_rpc.jsonrpc')

Once activated, the following happens:

#. The :meth:`pyramid_rpc.jsonrpc.add_jsonrpc_endpoint` directive is added to
   the ``config`` instance.

#. The :meth:`pyramid_rpc.jsonrpc.add_jsonrpc_method` directive is added to
   the ``config`` instance.

#. An exception view is registered for
   :class:`pyramid_rpc.jsonrpc.JsonRpcError` exceptions.

Usage
=====

After including the ``pyramid_rpc.jsonrpc`` package in your project, you can
add an :term:`endpoint` for handling incoming requests. After that, attach
several methods to the endpoint to handle specific functions within your api.

Adding a JSON-RPC Endpoint
--------------------------

An :term:`endpoint` is added via the
:func:`~pyramid_rpc.jsonrpc.add_jsonrpc_endpoint` directive on the
``config`` instance.

Example:

.. code-block:: python

    config = Configurator()
    config.include('pyramid_rpc.jsonrpc')
    config.add_jsonrpc_endpoint('api', '/api/jsonrpc')

It is possible to add multiple endpoints as well as pass extra arguments to
:func:`~pyramid_rpc.jsonrpc.add_jsonrpc_endpoint` to handle traversal, which
can assist in adding security to your RPC API.

Exposing JSON-RPC Methods
-------------------------

Methods on your API are exposed by attaching views to an :term:`endpoint`.
Methods may be attached via the
:func:`~pyramid_rpc.jsonrpc.add_jsonrpc_method` which is a thin wrapper
around :meth:`pyramid.config.Configurator.add_view` method.

Example:

.. code-block:: python

    def say_hello(request, name):
        return 'Hello, ' + name

    config.add_jsonrpc_method(say_hello, endpoint='api', method='say_hello')

If you prefer, you can use the :func:`~pyramid_rpc.jsonrpc.jsonrpc_method`
view decorator to declare your methods closer to your actual code.
Remember when using this lazy configuration technique, it's always necessary
to call :meth:`pyramid.config.Configurator.scan` from within your setup code.

.. code-block:: python

    from pyramid_rpc.jsonrpc import jsonrpc_method

    @jsonrpc_method(endpoint='api')
    def say_hello(request, name):
        return 'Hello, ' + name

    config.scan()

To set the RPC method to something other than the name of the view, specify
the ``method`` parameter:

.. code-block:: python

    from pyramid_rpc.jsonrpc import jsonrpc_method

    @jsonrpc_method(method='say_hello', endpoint='api')
    def say_hello_view(request, name):
        return 'Hello, ' + name

    config.scan()

Because methods are a thin layer around Pyramid's views, it is possible to add
extra view predicates to the method, as well as ``permission`` requirements.

Handling JSON-RPC Batch Requests
--------------------------------

Batch requests are handled automatically. A JSON-RPC batch request consists
of an array of regular JSON-RPC requests; the response will consist of an
array of the responses.

If there are no responses (which happens only when the request consisted
entirely of notifications, to which there can be no response), the batch
response is an empty body. This is not a valid JSON value, but the JSON-RPC
spec does not provide for any other response in this situation.

.. _jsonrpc_custom_renderers:

Custom Renderers
----------------

By default, responses are rendered using the Python standard library's
:func:`json.dumps`. This can be changed the same way any renderer is
changed in Pyramid. See the `Pyramid Renderers
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/renderers.html>`_
chapter for extra details. As an example, let's update an :term:`endpoint` to
use Pyramid 1.4's cool new :class:`pyramid.renderers.JSON` renderer which
supports custom adapters.

.. code-block:: python

    from pyramid.renderers import JSON

    json_renderer = JSON()
    json_renderer.add_adapter(datetime.datetime, lambda v, request: v.isoformat())
    config.add_renderer('myjson', json_renderer)

    config.add_jsonrpc_endpoint('api', '/api', default_renderer='myjson')

A ``default_renderer`` can be specified on an :term:`endpoint`, which will
propagate to all methods attached to the endpoint. Optionally, an individual
method can also override the renderer.

View Mappers
------------

A view mapper is registered for JSON-RPC methods by default which will
match the arguments from ``request.rpc_args`` to the parameters of the
view. Optional arguments are allowed and an error will be returned if too
many or too few arguments are supplied to the view.

This default view mapper may be overridden by setting the
``default_mapper`` option on :func:`~pyramid_rpc.jsonrpc.add_jsonrpc_endpoint`
or the ``mapper`` option when using :func:`~pyramid_rpc.jsonrpc.jsonrpc_method`
or :func:`~pyramid_rpc.jsonrpc.add_jsonrpc_method`.

HTTP GET and POST Support
-------------------------

As of ``pyramid_rpc`` version 0.5, JSON-RPC requests can be made using
HTTP GET. By default, an endpoint will accept requests from both ``GET``
and ``POST`` methods. This can be controlled on either the :term:`endpoint`
or on an individual method by using the ``request_method`` predicate. For
example, to limit requests to only ``POST`` requests:

.. code-block:: python

   config.add_jsonrpc_endpoint('api', '/api', request_method='POST')

Batch requests are not supported via HTTP GET; there is no way to send multiple
requests with the HTTP GET semantics.

Handling JSONP Requests
-----------------------

Pyramid comes with a :class:`pyramid.renderers.JSONP` which can be registered
for the endpoint, using the method described within
:ref:`jsonrpc_custom_renderers`.

.. _jsonrpc_api:

API
===

.. automodule:: pyramid_rpc.jsonrpc

  .. autofunction:: includeme

  .. autofunction:: add_jsonrpc_endpoint

  .. autofunction:: add_jsonrpc_method

  .. autofunction:: jsonrpc_method

Exceptions
----------

  .. autoclass:: JsonRpcError

  .. autoclass:: JsonRpcParseError

  .. autoclass:: JsonRpcRequestInvalid

  .. autoclass:: JsonRpcMethodNotFound

  .. autoclass:: JsonRpcParamsInvalid

  .. autoclass:: JsonRpcInternalError
