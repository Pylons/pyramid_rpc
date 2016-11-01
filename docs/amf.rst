.. _amf:

=========================
Action Message Format RPC
=========================

Action Message Format (AMF) is a binary format used for serializing
ActionScript objects. It's primarily used for communication between Flash and
a server, though it can be used from clients in other languages as well.

AMF support is provided by utilizing the `PyAMF package <http://pyamf.org/index.html>`_.

:mod:`pyramid_rpc` exposes AMF as a Remoting gateway in a similar manner to
PyAMF's Django gateway support. This allows a remoting gateway to be exposed
as a normal Pyramid view.

Exposing AMF Services
=====================

Exposing functions for AMF remoting is done by setting up standard AMF
functions and defining a gateway view::
    
    # yourproject/amfgateway.py
    
    from pyramid_rpc.amfgateway import PyramidGateway
    
    def echo(request, data):
        return data

    services = {
        'myservice.echo': echo
        # could include other functions as well
    }

    echoGateway = PyramidGateway(services)

Then expose the gateway as if it was a standard Pyramid view::
    
    # yourproject/run.py
    
    from pyramid.config import Configurator
    from wsgiref.simple_server import make_server
    
    if __name__ == '__main__':
        config = Configurator()
        config.add_view('amfgateway.echoGateway')
        app = config.make_wsgi_app()
        server = make_server('', 8080, app)
        server.serve_forever()

The request passed into the service function is the standard Pyramid request
object. It can be disabled by passing ``expose_request=False`` into the
PyramidGateway instantiation.

.. seealso::
    `PyAMF documentation <http://www.pyamf.org/>`_
    
    `Django Gateway documentation (PyramidGateway is based on this work) <http://www.pyamf.org/tutorials/gateways/django.html>`_

.. _amf_api:

API
===

Public
------

.. automodule:: pyramid_rpc.amfgateway

  .. autoclass:: PyramidGateway
