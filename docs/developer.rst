.. _developer:

=================================
Developing Additional RPC Support
=================================

:mod:`pyramid_rpc` is a community developed and support package. As such, the
developers primarily support the RPC methods they actually use. Contributors
are welcome to add support for their preferred RPC method, and an API is
available to ease the view lookup task when desired.

Contributions should follow the `Pylons Project Community guidelines.
<http://docs.pylonsproject.org/#contributing>`_ and include appropriate unit
tests, with nosetest skip's for developers to run tests that don't have
dependent RPC packages installed.

.. _api:

API
===

Public
------

.. automodule:: pyramid_rpc.api

  .. autofunction:: view_lookup
