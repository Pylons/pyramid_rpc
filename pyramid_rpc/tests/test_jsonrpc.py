import unittest

from pyramid import testing
from pyramid.compat import json

from webtest import TestApp

class TestJSONRPCIntegration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, app, method, params, id=5, version='2.0',
                 path='/api/jsonrpc', content_type='application/json'):
        body = {}
        if id is not None:
            body['id'] = id
        if version is not None:
            body['jsonrpc'] = version
        if method is not None:
            body['method'] = method
        if params is not None:
            body['params'] = params
        resp = app.post(path, content_type=content_type,
                        params=json.dumps(body))
        if id is not None:
            self.assertEqual(resp.status_int, 200)
            self.assertEqual(resp.content_type, 'application/json')
            result = json.loads(resp.body)
            self.assertEqual(result['jsonrpc'], '2.0')
            self.assertEqual(result['id'], id)
        else:
            self.assertEqual(resp.status_int, 204)
            result = resp.body
        return result

    def test_add_jsonrpc_method_with_no_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, method='dummy')

    def test_add_jsonrpc_method_with_no_method(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, endpoint='rpc')

    def test_it(self):
        def view(request, a, b):
            return {'a': a, 'b': b}
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['result'], {'a': 2, 'b': 3})

    def test_it_with_no_mapper(self):
        def view(request):
            return request.rpc_args[0]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy',
                                  mapper=None)
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['result'], 2)

    def test_it_with_multiple_methods(self):
        def view(request, a, b):
            return a
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        config.add_jsonrpc_method(lambda r: 'fail',
                                  endpoint='rpc', method='dummy2')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['result'], 2)

    def test_it_with_no_version(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3], version=None)
        self.assertEqual(result['error']['code'], -32600)

    def test_it_with_no_method(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, None, [2, 3])
        self.assertEqual(result['error']['code'], -32600)

    def test_it_with_no_id(self):
        def view(request, a, b):
            return a
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3], id=None)
        self.assertEqual(result, '')

    def test_it_with_no_params(self):
        def view(request):
            self.assertEqual(request.rpc_args, ())
            return 'no params'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', None)
        self.assertEqual(result['result'], 'no params')

    def test_it_with_named_params(self):
        def view(request, three, four, five):
            self.assertEqual('%s%s%s'%(three,four,five), '345')
            return 'named params'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', {'four':4, 'five':5, 'three':3})
        self.assertEqual(result['result'], 'named params')

    def test_it_with_named_params_and_default_values(self):
        def view(request, three, four = 4 , five = 'foo' ):
            self.assertEqual('%s%s%s'%(three,four,five), '345')
            return 'named params'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', { 'five':5, 'three':3})
        self.assertEqual(result['result'], 'named params')

    def test_it_with_invalid_method(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'foo', [2, 3])
        self.assertEqual(result['error']['code'], -32601)

    def test_it_with_invalid_body(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params='{')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32700)

    def test_it_with_general_exception(self):
        def view(request, a, b):
            raise Exception
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['error']['code'], -32603)

    def test_it_with_cls_view(self):
        class view(object):
            def __init__(self, request):
                self.request = request

            def foo(self, a, b):
                return [a, b]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy',
                                  attr='foo')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['result'], [2, 3])

    def test_it_with_named_args_and_cls_view(self):
        class view(object):
            def __init__(self, request):
                self.request = request

            def foo(self, a, b):
                return [a, b]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy',
                                  attr='foo')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', {'b':3, 'a':2})
        self.assertEqual(result['result'], [2, 3])

    def test_it_with_default_args(self):
        def view(request, a, b, c='bar'):
            return [a, b, c]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['result'], [2, 3, 'bar'])

    def test_it_with_missing_args(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(lambda r, a, b: a,
                                  endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2])
        self.assertEqual(result['error']['code'], -32602)

    def test_it_with_too_many_args(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(lambda r, a, b: a,
                                  endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [2, 3, 4])
        self.assertEqual(result['error']['code'], -32602)

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

class TestJSONRPCFixture(unittest.TestCase):
    package = 'pyramid_rpc.tests.fixtures.jsonrpc'

    def _callFUT(self, app, method, params, id=5, version='2.0',
                 path='/api/jsonrpc', content_type='application/json'):
        body = {}
        if id is not None:
            body['id'] = id
        if version is not None:
            body['jsonrpc'] = version
        if method is not None:
            body['method'] = method
        if params is not None:
            body['params'] = params
        resp = app.post(path, content_type=content_type,
                        params=json.dumps(body))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['id'], id)
        return result

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

    def tearDown(self):
        testing.tearDown()

    def test_basic(self):
        result = self._callFUT(self.testapp, 'basic', [])
        self.assertEqual(result['result'], 'basic')

    def test_exc(self):
        result = self._callFUT(self.testapp, 'exc', [])
        self.assertEqual(result['error']['code'], -32603)

    def test_decorated_method(self):
        result = self._callFUT(self.testapp, 'create', [1, 2])
        self.assertEqual(result['result'], {'create':'bob'})

    def test_decorated_class_method(self):
        result = self._callFUT(self.testapp, 'say_hello', ['bob'])
        self.assertEqual(result['result'], 'hello, bob')

    def test_secure_hello_with_credentials(self):
        self.auth_policy.userid = 'bob'
        result = self._callFUT(self.testapp, 'secure_hello', ['bob'],
                               path='/api/jsonrpc/secure')
        self.assertEqual(result['result'], 'hello, bob')

    def test_secure_hello_with_no_credentials(self):
        result = self._callFUT(self.testapp, 'secure_hello', ['bob'],
                               path='/api/jsonrpc/secure')
        self.assertEqual(result['result'], 'hello, bob')

    def test_secure_echo_with_credentials(self):
        self.auth_policy.userid = 'bob'
        result = self._callFUT(self.testapp, 'secure_echo', ['foo'],
                               path='/api/jsonrpc/secure')
        self.assertEqual(result['result'], 'foo')

    def test_secure_echo_with_no_credentials(self):
        result = self._callFUT(self.testapp, 'secure_echo', ['bob'],
                               path='/api/jsonrpc/secure')
        self.assertEqual(result['error']['code'], -32600)

