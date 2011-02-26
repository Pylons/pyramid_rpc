.. _index:

===================
Pyramid RPC Support
===================

:mod:`pyramid_rpc` provides :term:`RPC` support for the :mod:`pyramid` web
framework.

Currently available RPC Implementations:

* `XML-RPC <http://www.xmlrpc.com/>`_
* `Action Message Format (AMF) via PyAMF <http://pyamf.org/index.html>`_

Implementations planned for:

* `JSON-RPC <http://json-rpc.org/wiki/specification>`_

File an issue on the `GitHub Issue Tracker for pyramid_rpc
<https://github.com/Pylons/pyramid_rpc/issues>`_ to request additional RPC's
to support. Patches and contributions welcome, please read the `Pylons Project
Community section first. <http://docs.pylonsproject.org/#contributing>`_.


Installation
============

:mod:`pyramid_rpc` is a package that ships outside the main :mod:`pyramid`
distribution. To install the package, use ``easy_install``::

  easy_install pyramid_rpc

Or obtain the packge via `http://github.com/Pylons/pyramid_rpc
<http://github.com/Pylons/pyramid_rpc>`_ and use ``python setup.py install``.

RPC Documentation
=================

.. toctree::
    :maxdepth: 2
    
    xmlrpc
    amf
    developer

.. _glossary:

Terminology
-----------

.. glossary::
    :sorted:

    RPC
        A Remote Procedure Call. See `Wikipedia entry on Remote procedure calls 
        <http://en.wikipedia.org/wiki/Remote_procedure_call>`_


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
