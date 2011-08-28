.. _jsonrpc:

========
JSON-RPC 
========

`pyramid_rpc` supports 
`JSON-RPC 2.0 Specification <http://groups.google.com/group/json-rpc/web/json-rpc-2-0>`_ .

Setup
=====

Use the ``includeme`` via ``config.include``:

.. code-block:: python

    config.include('pyramid_rpc.jsonrpc')

Once activated, the following happens:

#. The :meth:`pyramid_rpc.jsonrpc.add_jsonrpc_endpoint` directive is added to
   the ``configurator`` instance.

#. The :meth:`pyramid_rpc.jsonrpc.add_jsonrpc_method` directive is added to
   the ``configurator`` instance.

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
``configurator`` instance.

Example:

.. code-block:: python

    config = Configurator()
    config.include('pyramid_rpc.jsonrpc')
    config.add_jsonrpc_endpoint('api', '/api/jsonrpc')

It is possible to add multiple endpoints as well as pass extra arguments to
``add_jsonrpc_endpoint`` to handle traversal, which can assist in adding
security to your RPC API.

Exposing JSON-RPC Methods
-------------------------

Methods on your API are exposed by attaching views to an :term:`endpoint`.
Methods may be attached via the
:func:`~pyramid_rpc.jsonrpc.add_jsonrpc_method` which is a thin wrapper
around Pyramid's ``add_view`` function.

Example:

.. code-block:: python

    def create_user_view(request, login, password):
        userid = 0 # create a new user
        return {
            'login': login,
            'id': userid,
        }

    from pyramid_rpc.jsonrpc import jsonrpc_method

    @jsonrpc_method(method='create', endpoint='api')
    def api_create(request, login):
        return {}

    config.add_jsonrpc_endpoint('api', '/api/jsonrpc')
    config.add_jsonrpc_method(create_user_view,
                              endpoint='api', method='users.createNew')

Because this is a thin layer around Pyramid's views, it is possible to add
extra view predicates to the method, as well as ``permission`` requirements.

View Mappers
------------

A view mapper is registered for JSON-RPC methods by default which will
match the arguments from ``request.rpc_args`` to the parameters of the
view. Optional arguments are allowed and an error will be returned if too
many or too few arguments are supplied to the view.

This default view mapper may be overridden by setting ``mapper=None``
when using :func:`~pyramid_rpc.jsonrpc.jsonrpc_method` or
:func:`~pyramid_rpc.jsonrpc.add_jsonrpc_method`. Of course, another mapper
may be specified as well.

.. _jsonrpc_api:

API
===

Public
------

.. automodule:: pyramid_rpc.jsonrpc

  .. autofunction:: includeme

  .. autofunction:: add_jsonrpc_endpoint

  .. autofunction:: add_jsonrpc_method

  .. autofunction:: jsonrpc_method

Exceptions
++++++++++

.. automodule:: pyramid_rpc.jsonrpc

  .. autoclass:: JsonRpcError

  .. autoclass:: JsonRpcParseError

  .. autoclass:: JsonRpcRequestInvalid

  .. autoclass:: JsonRpcMethodNotFound

  .. autoclass:: JsonRpcParamsInvalid

  .. autoclass:: JsonRpcInternalError
