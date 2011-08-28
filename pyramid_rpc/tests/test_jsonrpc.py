import unittest
import warnings

from pyramid import testing
from pyramid.compat import json

from webtest import TestApp

class TestJSONRPCIntegration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], 2)

    def test_it_with_no_version(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'method': 'dummy', 'id': 5, 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32600)

    def test_it_with_no_method(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'id': 5, 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 204)
        self.assertEqual(resp.body, '')

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
        params = {'jsonrpc': '2.0', 'id': 5, 'method': 'dummy'}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], 'no params')

    def test_it_with_invalid_method(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'id': 5, 'method': 'foo', 'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
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
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], [2, 3, 'bar'])

    def test_it_with_missing_args(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(lambda r, a, b: a,
                                  endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32602)

    def test_it_with_too_many_args(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(lambda r, a, b: a,
                                  endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'dummy', 'id': 5,
                  'params': [2, 3, 4]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['error']['code'], -32602)


class TestJSONRPCMethodDecorator(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_it(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('api', '/api/jsonrpc')
        config.scan('pyramid_rpc.tests.fixtures.jsonrpc')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'create', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], {'create': 'bob'})

    def test_it_with_method_from_view_name(self):
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('api', '/api/jsonrpc')
        config.scan('pyramid_rpc.tests.fixtures.jsonrpc_method_default')
        app = config.make_wsgi_app()
        app = TestApp(app)
        params = {'jsonrpc': '2.0', 'method': 'create', 'id': 5,
                  'params': [2, 3]}
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(params))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.content_type, 'application/json')
        result = json.loads(resp.body)
        self.assertEqual(result['id'], 5)
        self.assertEqual(result['jsonrpc'], '2.0')
        self.assertEqual(result['result'], {'create': 'bob'})

    def test_it_no_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('api', '/api/jsonrpc')
        self.assertRaises(ConfigurationError, config.scan,
                          'pyramid_rpc.tests.fixtures.jsonrpc_no_endpoint')

