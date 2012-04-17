from pyramid.security import Allow
from pyramid.security import Authenticated

from pyramid_rpc.jsonrpc import jsonrpc_method
from pyramid_rpc.xmlrpc import xmlrpc_method

ACLS = {
    'hello': [
        (Allow, Authenticated, 'view'),
    ],
}

class Root(dict):

    def __init__(self, request):
        self.request = request
        self.__acl__ = ACLS.get(request.rpc_method)

def basic(request):
    return 'basic'

@jsonrpc_method(method='exc', endpoint='jsonapi')
@xmlrpc_method(method='exc', endpoint='xmlapi')
def exc_view(request):
    raise Exception()

@jsonrpc_method(method='create', endpoint='jsonapi')
@xmlrpc_method(method='create', endpoint='xmlapi')
def create_view(request, a, b):
    return 'create %s %s' % (a, b)

class RPCHandler(object):
    def __init__(self, request):
        self.request = request

    @jsonrpc_method(method='class_hello', endpoint='jsonapi')
    @xmlrpc_method(method='class_hello', endpoint='xmlapi')
    def class_based_hello(self, name):
        return 'hello, ' + name

@jsonrpc_method(method='hello', endpoint='jsonapi')
@xmlrpc_method(method='hello', endpoint='xmlapi')
def basic_hello(request, name):
    return 'hello, %s, stranger' % name

@jsonrpc_method(method='hello', endpoint='secure_jsonapi', permission='view')
@xmlrpc_method(method='hello', endpoint='secure_xmlapi', permission='view')
def auth_hello(request, name):
    return 'hello, %s, friend' % name

def includeme(config):
    config.include('pyramid_rpc.jsonrpc')
    config.include('pyramid_rpc.xmlrpc')

    config.add_jsonrpc_endpoint('jsonapi', '/api/jsonrpc')
    config.add_xmlrpc_endpoint('xmlapi', '/api/xmlrpc')

    config.add_jsonrpc_method(basic, endpoint='jsonapi', method='basic')
    config.add_xmlrpc_method(basic, endpoint='xmlapi', method='basic')

    config.add_jsonrpc_endpoint(
        'secure_jsonapi', '/api/jsonrpc/secure', factory=Root)
    config.add_xmlrpc_endpoint(
        'secure_xmlapi', '/api/xmlrpc/secure', factory=Root)

    config.scan('.')
