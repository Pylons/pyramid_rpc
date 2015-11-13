import json
import unittest

from pyramid import testing

from webtest import TestApp


class Test_add_jsonrpc_method(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('pyramid_rpc.jsonrpc')

    def tearDown(self):
        testing.tearDown()

    def test_with_undefined_endpoint(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, endpoint='rpc', method='foo')

    def test_with_missing_endpoint_param(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, method='dummy')

    def test_with_no_method_param(self):
        from pyramid.exceptions import ConfigurationError
        config = self.config
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        self.assertRaises(ConfigurationError,
                          config.add_jsonrpc_method,
                          lambda r: None, endpoint='rpc')


class TestJSONRPCIntegration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, app, method, params, id=5, version='2.0',
                 path='/api/jsonrpc', content_type='application/json',
                 expect_error=False):
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
        if id is not None or expect_error:
            self.assertEqual(resp.content_type, 'application/json')
            result = resp.json
            self.assertEqual(result['jsonrpc'], '2.0')
            self.assertEqual(result['id'], id)
        else:
            result = resp.json
            self.assertEqual(result, '')
        return result

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

    def test_it_with_batched_requests(self):
        def view(request, a, b):
            return [a, b]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        body = [
            {'id': 1, 'jsonrpc': '2.0', 'method': 'dummy', 'params': [2, 3]},
            {'id': 2, 'jsonrpc': '2.0', 'method': 'dummy', 'params': {'a': 3, 'b': 2}},
        ]
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(body))
        self.assertEqual(resp.status_int, 200)
        result = resp.json
        result1 = [r for r in result if r['id'] == 1][0]
        result2 = [r for r in result if r['id'] == 2][0]
        self.assertEqual(result1, {'id': 1, 'jsonrpc': '2.0', 'result': [2, 3]})
        self.assertEqual(result2, {'id': 2, 'jsonrpc': '2.0', 'result': [3, 2]})

    def test_it_with_batched_requests_and_content_length(self):
        def view(request, a):
            return [a]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        body = [
            {'id': 1, 'jsonrpc': '2.0', 'method': 'dummy', 'params': [0]},
            {'id': 2, 'jsonrpc': '2.0', 'method': 'dummy', 'params': [[x for x in range(100)]]},
        ]
        json_body = json.dumps(body, separators=(',',':'))
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        headers={'Content-Length': str(len(json_body))}, params=json_body)
        self.assertEqual(resp.status_int, 200)
        result = resp.json
        result1 = [r for r in result if r['id'] == 1][0]
        result2 = [r for r in result if r['id'] == 2][0]
        self.assertEqual(result1, {'id': 1, 'jsonrpc': '2.0', 'result': [0]})
        self.assertEqual(result2, {'id': 2, 'jsonrpc': '2.0', 'result': [[x for x in range(100)]]})

    def test_it_with_batched_requests_and_more_predicates(self):
        # View ordering is determined partially by number of predicates
        class MoodPredicate(object):
            def __init__(self, val, config):
                self.val = val

            def text(self):
                return 'mood predicate = %s' % self.val

            phash = text

            def __call__(self, context, request):
                if isinstance(request.rpc_args, list):
                    compare = request.rpc_args[0]
                else:
                    compare = request.rpc_args['mood']
                return compare == self.val

        class ColorPredicate(object):
            def __init__(self, val, config):
                self.val = val

            def text(self):
                return 'color predicate = %s' % self.val

            phash = text

            def __call__(self, context, request):
                if isinstance(request.rpc_args, list):
                    compare = request.rpc_args[1]
                else:
                    compare = request.rpc_args['color']
                return compare == self.val

        def view(request, mood, color):
            return [mood, color]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_view_predicate('mood', MoodPredicate)
        config.add_view_predicate('color', ColorPredicate)
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy', mood='happy', color='yellow')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy', mood='sad', color='blue')
        app = config.make_wsgi_app()
        app = TestApp(app)
        body = [
            {'id': 1, 'jsonrpc': '2.0', 'method': 'dummy', 'params': ['happy', 'yellow']},
            {'id': 2, 'jsonrpc': '2.0', 'method': 'dummy', 'params': {'color': 'blue', 'mood': 'sad'}},
        ]
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(body))
        self.assertEqual(resp.status_int, 200)
        result = resp.json
        result1 = [r for r in result if r['id'] == 1][0]
        result2 = [r for r in result if r['id'] == 2][0]
        self.assertEqual(result1, {'id': 1, 'jsonrpc': '2.0', 'result': ['happy', 'yellow']})
        self.assertEqual(result2, {'id': 2, 'jsonrpc': '2.0', 'result': ['sad', 'blue']})

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

    def test_it_with_batched_notifications(self):
        # a notification is a request with no id
        def view(request, a, b):
            return [a, b]
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        body = [
            {'jsonrpc': '2.0', 'method': 'dummy', 'params': [2, 3]},
            {'jsonrpc': '2.0', 'method': 'dummy', 'params': {'a': 3, 'b': 2}},
        ]
        resp = app.post('/api/jsonrpc', content_type='application/json',
                        params=json.dumps(body))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, b'')

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
        result = resp.json
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

    def test_it_with_rpc_error(self):
        from pyramid_rpc.jsonrpc import JsonRpcError
        def view(request):
            raise JsonRpcError(code=500, message='dummy')
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [])
        self.assertEqual(result['error']['code'], 500)
        self.assertEqual(result['error']['message'], 'dummy')
        self.assertFalse('data' in result['error'])

    def test_it_with_rpc_error_with_data(self):
        from pyramid_rpc.jsonrpc import JsonRpcError
        def view(request):
            raise JsonRpcError(code=500, message='dummy', data='foo')
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [])
        self.assertEqual(result['error']['code'], 500)
        self.assertEqual(result['error']['message'], 'dummy')
        self.assertEqual(result['error']['data'], 'foo')

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

    def test_it_error_with_no_id(self):
        def view(request):
            raise Exception
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [], id=None, expect_error=True)
        self.assertEqual(result['error']['code'], -32603)

    def test_it_with_decorator(self):
        def view(request):
            return 'foo'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        dummy_decorator = DummyDecorator()
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy',
                                  decorator=dummy_decorator)
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [])
        self.assertEqual(result['result'], 'foo')
        self.assertTrue(dummy_decorator.called)

    def test_it_with_default_mapper(self):
        def view(request):
            return request.rpc_args
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc', default_mapper=None)
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', ['a', 'b', 'c'])
        self.assertEqual(result['result'], ['a', 'b', 'c'])

    def test_override_default_mapper(self):
        from pyramid_rpc.mapper import MapplyViewMapper
        def view(request, a, b, c):
            return (a, b, c)
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc', default_mapper=None)
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy',
                                  mapper=MapplyViewMapper)
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', ['a', 'b', 'c'])
        self.assertEqual(result['result'], ['a', 'b', 'c'])

    def test_it_with_default_renderer(self):
        def view(request):
            return 'bar'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        dummy_renderer = DummyRenderer('foo')
        config.add_renderer('jsonrpc', dummy_renderer)
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc',
                                    default_renderer='jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [])
        self.assertEqual(result['result'], 'foo')
        self.assertEqual(dummy_renderer.called, True)

    def test_override_default_renderer(self):
        def view(request):
            return 'bar'
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        dummy_renderer = DummyRenderer('foo')
        dummy_renderer2 = DummyRenderer('baz')
        config.add_renderer('jsonrpc', dummy_renderer)
        config.add_renderer('jsonrpc2', dummy_renderer2)
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc',
                                    default_renderer='jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy',
                                  renderer='jsonrpc2')
        app = config.make_wsgi_app()
        app = TestApp(app)
        result = self._callFUT(app, 'dummy', [])
        self.assertEqual(result['result'], 'baz')
        self.assertEqual(dummy_renderer.called, False)
        self.assertEqual(dummy_renderer2.called, True)

    def test_nonascii_request(self):
        def view(request, a):
            return a
        config = self.config
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')
        app = config.make_wsgi_app()
        app = TestApp(app)
        val = b'S\xc3\xa9bastien'.decode('utf-8')
        result = self._callFUT(app, 'dummy', [val])
        self.assertEqual(result['result'], val)


class TestGET(unittest.TestCase):

    def setUp(self):
        def view(request, a, b=3):
            return [a, b]
        self.config = config = testing.setUp()
        config.include('pyramid_rpc.jsonrpc')
        config.add_jsonrpc_endpoint('rpc', '/api/jsonrpc')
        config.add_jsonrpc_method(view, endpoint='rpc', method='dummy')

    def tearDown(self):
        testing.tearDown()

    def _makeTestApp(self):
        app = self.config.make_wsgi_app()
        app = TestApp(app)
        return app

    def _callFUT(self, app, method, params, id='5', version='2.0',
                 path='/api/jsonrpc', expect_error=False):
        qitems = []
        if id is not None:
            qitems.append(('id', id))
        if version is not None:
            qitems.append(('jsonrpc', version))
        if method is not None:
            qitems.append(('method', method))
        if params is not None:
            if isinstance(params, str):
                qitems.append(('params', params))
            else:
                qitems.append(('params', json.dumps(params)))
        #import pdb; pdb.set_trace()
        resp = app.get(path, params=qitems)
        self.assertEqual(resp.status_int, 200)
        if id is not None or expect_error:
            self.assertEqual(resp.content_type, 'application/json')
            result = resp.json
            self.assertEqual(result['jsonrpc'], '2.0')
            self.assertEqual(result['id'], id)
        else:
            result = resp.json
            self.assertEqual(result, '')
        return result

    def test_it(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', [2, 3])
        self.assertEqual(result['result'], [2, 3])

    def test_it_named_args(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', {'a': 2, 'b': 3})
        self.assertEqual(result['result'], [2, 3])

    def test_it_with_default_args(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', [2])
        self.assertEqual(result['result'], [2, 3])

    def test_it_with_too_few_args(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', [])
        self.assertEqual(result['error']['code'], -32602)

    def test_it_with_too_many_args(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', [2, 3, 4])
        self.assertEqual(result['error']['code'], -32602)

    def test_it_with_unparseable_args(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', 'foo', id=None, expect_error=True)
        self.assertEqual(result['error']['code'], -32700)

    def test_it_with_missing_args(self):
        app = self._makeTestApp()
        result = self._callFUT(app, 'dummy', None)
        self.assertEqual(result['error']['code'], -32602)

    def test_it_with_no_id(self):
        app = self._makeTestApp()
        self._callFUT(app, 'dummy', [2, 3], id=None)

    def test_it_error_with_no_id(self):
        def view(request):
            raise Exception
        config = self.config
        config.add_jsonrpc_method(view, endpoint='rpc', method='err')
        app = self._makeTestApp()
        result = self._callFUT(app, 'err', [], id=None, expect_error=True)
        self.assertEqual(result['error']['code'], -32603)

    def test_PUT(self):
        app = self._makeTestApp()
        response = app.put('/api/jsonrpc')
        result = response.json_body
        self.assertEqual(result['error']['code'], -32600)

    def test_DELETE(self):
        app = self._makeTestApp()
        response = app.delete('/api/jsonrpc')
        result = response.json_body
        self.assertEqual(result['error']['code'], -32600)


class DummyDecorator(object):
    called = False

    def __call__(self, view):
        def wrapper(context, request):
            self.called = True
            return view(context, request)
        return wrapper


class DummyRenderer(object):
    called = False

    def __init__(self, result):
        self.result = result

    def __call__(self, info):
        def _render(value, system):
            self.called = True
            value['result'] = self.result
            return json.dumps(value)
        return _render
