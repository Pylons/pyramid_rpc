import sys

py_version = sys.version_info[:2]
PY3 = py_version[0] == 3

if PY3: # pragma: no cover
    import xmlrpc.client as xmlrpclib
else:
    import xmlrpclib
