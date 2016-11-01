.. _index:

===================
Pyramid RPC Support
===================

:mod:`pyramid_rpc` provides :term:`RPC` support for the :mod:`pyramid` web
framework.

Currently available RPC Implementations:

* `XML-RPC <http://www.xmlrpc.com/>`_
* `JSON-RPC <http://jsonrpc.org/specification>`_
* `Action Message Format (AMF) via PyAMF <http://pyamf.org/index.html>`_

File an issue on the `GitHub Issue Tracker for pyramid_rpc
<https://github.com/Pylons/pyramid_rpc/issues>`_ to request additional RPC's
to support. Patches and contributions welcome, please read the `Pylons Project
Community section first <http://docs.pylonsproject.org/#contributing>`_.


Installation
============

Install using ``pip``, where ``$VENV`` is the path to a virtual environment.

.. code-block:: bash

  $ $VENV/bin/pip install pyramid_rpc

Or obtain the packge via https://github.com/Pylons/pyramid_rpc
and use ``$VENV/bin/pip install -e .``.

RPC Documentation
=================

.. toctree::
    :maxdepth: 2

    xmlrpc
    jsonrpc
    amf
    developer
    changes

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`glossary`

.. toctree::
   :hidden:

   glossary
