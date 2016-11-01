RPC Services for Pyramid
========================

.. image:: https://travis-ci.org/Pylons/pyramid_rpc.png?branch=master
        :target: https://travis-ci.org/Pylons/pyramid_rpc

.. image:: https://readthedocs.org/projects/pyramid_rpc/badge/?version=latest
        :target: http://docs.pylonsproject.org/projects/pyramid-rpc/en/latest/
        :alt: Latest Documentation Status

``pyramid_rpc`` is a package of RPC related add-on's to make it easier to
create RPC services.

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

Support and Documentation
-------------------------

See the `pyramid_rpc website
<http://docs.pylonsproject.org/projects/pyramid_rpc/en/latest/>`_ to view
documentation, report bugs, and obtain support.

License
-------

``pyramid_rpc`` is offered under the BSD-derived `Repoze Public License
<http://repoze.org/license.html>`_.

Authors
-------

``pyramid_rpc`` is made available by `Agendaless Consulting
<http://agendaless.com>`_ and a team of contributors.
