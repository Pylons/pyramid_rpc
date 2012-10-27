import json
import unittest

from webtest import TestApp

from pyramid_rpc.compat import xmlrpclib

class DummyAuthenticationPolicy(object):
    userid = None
    groups = ()

    def authenticated_userid(self, request):
        return self.userid

    def effective_principals(self, request):
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        principals = [Everyone]
        userid = self.authenticated_userid(request)
        if userid:
            principals += [Authenticated]
            principals += [userid]
            principals += self.groups
        return principals

class RPCError(Exception):
    code = None
    message = None

    def __init__(self, code, message):
        self.code = code
        self.message = message

class SimpleRPCFixture(object):
    package = 'pyramid_rpc.tests.fixtures.simplerpc'
    path = None
    secure_path = None
    content_type = None

    def callFUT(self, path, method, body):
        """ Should raise RPCError if call fails."""
        return self.testapp.post(path,
                                 content_type=self.content_type,
                                 params=body)

    def setUp(self):
        from pyramid.config import Configurator
        from pyramid.authorization import ACLAuthorizationPolicy
        config = Configurator(package=self.package)
        config.include(self.package)
        self.auth_policy = DummyAuthenticationPolicy()
        config.set_authentication_policy(self.auth_policy)
        config.set_authorization_policy(ACLAuthorizationPolicy())
        app = config.make_wsgi_app()
        self.testapp = TestApp(app)
        self.config = config
        self.config.begin()

    def tearDown(self):
        self.config.end()

    def test_basic(self):
        result = self.callFUT(self.path, 'basic', ())
        self.assertEqual(result, 'basic')

    def test_exc(self):
        self.assertRaises(RPCError, self.callFUT, self.path, 'exc', ())

    def test_decorated_method(self):
        result = self.callFUT(self.path, 'create', (1, 2))
        self.assertEqual(result, 'create 1 2')

    def test_decorated_class_method(self):
        result = self.callFUT(self.path, 'class_hello', ('bob',))
        self.assertEqual(result, 'hello, bob')

    def test_basic_hello(self):
        result = self.callFUT(self.path, 'hello', ('bob',))
        self.assertEqual(result, 'hello, bob, stranger')

    def test_secure_hello_with_credentials(self):
        self.auth_policy.userid = 'bob'
        result = self.callFUT(self.secure_path, 'hello', ('bob',))
        self.assertEqual(result, 'hello, bob, friend')

    def test_secure_hello_with_no_credentials(self):
        self.assertRaises(RPCError, self.callFUT,
                          self.secure_path, 'hello', ('bob',))

class TestJSONRPC(SimpleRPCFixture, unittest.TestCase):
    path = '/api/jsonrpc'
    secure_path = '/api/jsonrpc/secure'
    content_type = 'application/json'

    def callFUT(self, path, method, params):
        body = {
            'id': 5,
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
        }
        resp = super(TestJSONRPC, self).callFUT(path, method, json.dumps(body))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = resp.json
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['id'], 5)
        if 'error' in result:
            raise RPCError(result['error']['code'], result['error']['message'])
        return result['result']

class TestXMLRPC(SimpleRPCFixture, unittest.TestCase):
    path = '/api/xmlrpc'
    secure_path = '/api/xmlrpc/secure'
    content_type = 'text/xml'

    def callFUT(self, path, method, params):
        body = xmlrpclib.dumps(params, methodname=method)
        resp = super(TestXMLRPC, self).callFUT(path, method, body)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'text/xml')
        try:
            result = xmlrpclib.loads(resp.body)[0][0]
        except xmlrpclib.Fault as e:
            raise RPCError(e.faultCode, e.faultString)
        return result
