from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import Everyone

ACLS = {
    'secure_echo': [
        (Allow, Authenticated, 'echo'),
    ],
    'secure_hello': [
        (Allow, Everyone, 'view'),
    ],
}

class Root(dict):

    def __init__(self, request):
        self.request = request
        self.__acl__ = ACLS[request.rpc_method]

