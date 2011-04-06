.. _xmlrpc:

=======
XML-RPC 
=======

XML-RPC allows you to expose one or more methods at a particular URL.
:mod:`pyramid_rpc` uses a view lookup pattern like that in :mod:`pyramid`
allowing the XML-RPC methods to be located with the rest of your views, or in
other packages.


Exposing XML-RPC Methods
========================

To expose XML-RPC methods, :mod:`pyramid_rpc` comes with a
:func:`~pyramid_rpc.xmlrpc_endpoint` view that uses view lookup. It will
locate a view configuration registered with the same ``route_name`` it was
configured with, and a ``name`` that is the same as the XML-RPC method name.

Example:

.. code-block:: python
   :linenos:
   
   @xmlrpc_view()
   def say_hello(request):
       return 'Hello, %s' % request.xmlrpc_args['name']

To set a different XML-RPC method name than the name of the function, pass
in a ``method`` parameter:

.. code-block:: python
    :linenos:
    
    @xmlrpc_view(method='say_hello')
    def echo(request):
        return 'Hello, %s' % request.xmlrpc_args['name']

Or if the route for the XML-RPC endpoint is not named 'RPC2':

.. code-block:: python
    :linenos:
    
    @xmlrpc_view(route_name='my_route')
    def say_hello(request):
        return 'Hello, %s' % request.xmlrpc_args['name']

Next, add the route to expose the XML-RPC endpoint. 

Using imperative code in your application's startup configuration:

.. code-block:: python
   :linenos:

   config.scan()
   config.add_route('RPC2', '/api/xmlrpc', view='pyramid_rpc.xmlrpc_endpoint')

If you don't wish to use the :class:`~pyramid_rpc.xmlrpc_view`
decorator, XML-RPC views can be added imperatively::

    from mypackage import say_hello
    config.add_view(say_hello, name='say_hello', route_name='RPC2')

Declarative Configuration
=========================

Using ZCML:

.. code-block:: xml
   :linenos:
   
   <route
       name="RPC2"
       pattern="/rpc"
       view="pyramid_rpc.xmlrpc_endpoint"
    />
   
   <view
     name="say_hello"
     view=".views.say_hello"
     route_name="RPC2"
     />

Call Example
============

Then call the function via an XML-RPC client.

.. code-block:: python
   :linenos:

   >>> from xmlrpclib import ServerProxy
   >>> s = ServerProxy('http://localhost:6543/api/xmlrpc')
   >>> s.say_hello(name='Chris')
   Hello, Chris


.. _xmlrpc_api:

API
===

Public
------

.. automodule:: pyramid_rpc.xmlrpc

  .. autoclass:: xmlrpc_view

  .. autofunction:: xmlrpc_endpoint

Internal Functions Used
-----------------------

.. automodule:: pyramid_rpc.xmlrpc

  .. autofunction:: xmlrpc_marshal

  .. autofunction:: parse_xmlrpc_request
