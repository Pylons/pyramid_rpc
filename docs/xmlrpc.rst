.. _xmlrpc:

=======
XML-RPC
=======

XML-RPC allows you to expose one or more methods at a particular URL.
:mod:`pyramid_rpc` uses a view lookup pattern like that in :mod:`pyramid`
allowing the XML-RPC methods to be located with the rest of your views, or in
other packages.

Setup
=====

Use the ``includeme`` via :meth:`pyramid.config.Configurator.include`:

.. code-block:: python

    config.include('pyramid_rpc.xmlrpc')

Once activated, the following happens:

#. The :meth:`pyramid_rpc.xmlrpc.add_xmlrpc_endpoint` directive is added to
   the ``config`` instance.

#. The :meth:`pyramid_rpc.xmlrpc.add_xmlrpc_method` directive is added to
   the ``config`` instance.

#. An exception view is registered for :class:`xmlrpclib.Fault` exceptions.

Usage
=====

After including the ``pyramid_rpc.xmlrpc`` package in your project, you can
add an :term:`endpoint` for handling incoming requests. After that, attach
several methods to the endpoint to handle specific functions within your api.

Adding a XML-RPC Endpoint
--------------------------

An :term:`endpoint` is added via the
:func:`~pyramid_rpc.xmlrpc.add_xmlrpc_endpoint` directive on the
``config`` instance.

Example:

.. code-block:: python

    config = Configurator()
    config.include('pyramid_rpc.xmlrpc')
    config.add_xmlrpc_endpoint('api', '/api/xmlrpc')

It is possible to add multiple endpoints as well as pass extra arguments to
:func:`~pyramid_rpc.xmlrpc.add_xmlrpc_endpoint` to handle traversal, which
can assist in adding security to your RPC API.

Exposing XML-RPC Methods
-------------------------

Methods on your API are exposed by attaching views to an :term:`endpoint`.
Methods may be attached via the
:func:`~pyramid_rpc.xmlrpc.add_xmlrpc_method` which is a thin wrapper
around Pyramid's :meth:`pyramid.config.Configurator.add_view` method.

Example:

.. code-block:: python

    def say_hello(request, name):
        return 'Hello, ' + name

    config.add_xmlrpc_method(say_hello, endpoint='api', method='say_hello')

If you prefer, you can use the :func:`~pyramid_rpc.xmlrpc.xmlrpc_method`
view decorator to declare your methods closer to your actual code.
Remember when using this lazy configuration technique, it's always necessary
to call :meth:`pyramid.config.Configurator.scan` from within your setup code.

.. code-block:: python

    from pyramid_rpc.xmlrpc import xmlrpc_method

    @xmlrpc_method(endpoint='api')
    def say_hello(request, name):
        return 'Hello, ' + name

    config.scan()

To set the RPC method to something other than the name of the view, specify
the ``method`` parameter:

.. code-block:: python

    from pyramid_rpc.xmlrpc import xmlrpc_method

    @xmlrpc_method(method='say_hello', endpoint='api')
    def say_hello_view(request, name):
        return 'Hello, ' + name

    config.scan()

Because methods are a thin layer around Pyramid's views, it is possible to add
extra view predicates to the method, as well as ``permission`` requirements.

Custom Renderers
----------------

By default, responses are rendered using the Python standard library's
:func:`xmlrpclib.dumps`. This can be changed the same way any renderer is
changed in Pyramid. See the `Pyramid Renderers
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/renderers.html>`_
chapter for extra details.

In addition, the built in renderer allows configuration by passing keyword
arguments to it. As an example, let's update an :term:`endpoint` to allow
marshalling ``None`` objects.

.. code-block:: python

    from pyramid_rpc.xmlrpc import XMLRPCRenderer

    config.add_renderer('myxmlrpc', XMLRPCRenderer(allow_none=True))
    config.add_xmlrpc_endpoint('api', '/api', default_renderer='myxmlrpc')


View Mappers
------------

A view mapper is registered for XML-RPC methods by default which will
match the arguments from ``request.rpc_args`` to the parameters of the
view. Optional arguments are allowed and an error will be returned if too
many or too few arguments are supplied to the view.

This default view mapper may be overridden by setting the
``default_mapper`` option on :func:`~pyramid_rpc.xmlrpc.add_xmlrpc_endpoint`
or the ``mapper`` option when using :func:`~pyramid_rpc.xmlrpc.xmlrpc_method`
or :func:`~pyramid_rpc.xmlrpc.add_xmlrpc_method`.


Call Example
============

Using Python's :mod:`xmlrpclib`, it's simple to instantiate a ``ServerProxy``
to call the function via an XML-RPC client.

.. code-block:: python
   :linenos:

   >>> from xmlrpclib import ServerProxy
   >>> s = ServerProxy('http://localhost:6543/api/xmlrpc')
   >>> s.say_hello(name='Chris')
   Hello, Chris


.. _xmlrpc_api:

API
===

.. automodule:: pyramid_rpc.xmlrpc

  .. autofunction:: includeme

  .. autofunction:: add_xmlrpc_endpoint

  .. autofunction:: add_xmlrpc_method

  .. autofunction:: xmlrpc_method

