.. _jsonrpc:

========
JSON-RPC 
========

`pyramid_rpc` supports 
`JSON-RPC 2.0 Specification <http://groups.google.com/group/json-rpc/web/json-rpc-2-0>`_ .

Exposing JSON-RPC Methods
===========================

A endpoint view for JSON-RPC is :func:`~pyramid_rpc.jsonrpc_endpoint`.
It will locate a view in a similar way that XML-RPC support.

Example:

.. code-block:: python
   :linenos:
   
   @rpc_view()
   def say_hello(request):
       return 'Hello, %s' % request.rpc_args['name']

Next, add the route to expose the JSON-RPC endpoint.

.. code-block:: python
   :linenos:

   config.scan()
   config.add_route('RPC2', '/api/jsonrpc', view='pyramid_rpc.jsonrpc_endpoint')

.. _jsonrpc_api:

API
======

Public
--------

.. automodule:: pyramid_rpc.jsonrpc

  .. autofunction:: jsonrpc_endpoint

Experimental
-------------

.. automodule:: pyramid_rpc.jsonrpc

  .. autoclass:: JsonRpcViewMapper

Internal Functions Used
-------------------------

.. automodule:: pyramid_rpc.jsonrpc
 
  .. autofunction:: jsonrpc_response
  .. autofunction:: jsonrpc_error_response
