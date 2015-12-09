import unittest

from pyramid import testing

try:
    import pyamf
    from pyamf import remoting, util
except ImportError: # pragma: nocover
    from nose import SkipTest
    raise SkipTest

class DummyLogging(object):
    def exception(self, *args):
        pass

    def debug(self, *args):
        pass

    def error(self, *args):
        pass

class TestAmfViewGateway(unittest.TestCase):
    def _makeOne(self, **kwargs):
        from pyramid_rpc.amfgateway import PyramidGateway
        return PyramidGateway(logger=DummyLogging(), **kwargs)

    def _makeRequestBody(self, service, body, raw=False):
        if not raw:
            body = [body]

        e = remoting.Envelope(pyamf.AMF3)
        e['/1'] = remoting.Request(service, body=body)
        return remoting.encode(e)

    def doRequest(self, body, gw_instance, request_method='POST', **kwargs):
        request = testing.DummyRequest(**kwargs)
        request.body = body
        request.method = request_method
        return gw_instance(request)

    def test_request_method(self):
        gw = self._makeOne()
        response = self.doRequest(None, gw, 'GET')
        self.assertEqual(response.status_int, 405)

    def test_bad_request(self):
        gw = self._makeOne()
        body = util.BufferedByteStream()
        body.write('Bad request')
        body.seek(0, 0)

        response = self.doRequest(body, gw)
        self.assertEqual(response.status_int, 400)

    def test_unknown_request(self):
        gw = self._makeOne()
        body = self._makeRequestBody('test.test', [], raw=True)

        response = self.doRequest(body, gw)

        envelope = remoting.decode(response.body)
        message = envelope['/1']

        self.assertEqual(message.status, remoting.STATUS_ERROR)
        body = message.body

        self.assertTrue(isinstance(body, remoting.ErrorFault))
        self.assertEqual(body.code, 'Service.ResourceNotFound')

    def test_eof_decode(self):
        gw = self._makeOne()
        gw.debug = True
        body = util.BufferedByteStream()
        body.seek(0, 0)
        response = self.doRequest(body, gw)
        assert 'The request body was unable to be successfully decoded' in response.detail
        assert 'Traceback' in response.detail
        self.assertEqual(response.status_int, 400)

    def _raiseException(self, e, *args, **kwargs):
        raise e()

    def _restoreEncode(self):
        remoting.encode = self.old_method

    def _restoreDecode(self):
        remoting.decode = self.old_method

    def test_really_bad_decode(self):
        self.old_method = remoting.decode
        remoting.decode = lambda *args, **kwargs: self._raiseException(Exception, *args, **kwargs)
        try:
            gw = self._makeOne()
            gw.debug = True
            request = util.BufferedByteStream()
            response = self.doRequest(request, gw)

            self.assertEqual(response.status_int, 500)
            assert 'Traceback' in response.detail
        finally:
            self._restoreDecode()

    def test_expected_exceptions_decode(self):
        self.old_method = remoting.decode
        try:
            gw = self._makeOne()
            request = util.BufferedByteStream()

            for x in (KeyboardInterrupt, SystemExit):
                remoting.decode = lambda *args, **kwargs: self._raiseException(x, *args, **kwargs)

                self.assertRaises(x, self.doRequest, request, gw)
        finally:
            self._restoreDecode()

    def test_expected_exception_response(self):
        gw = self._makeOne()
        request = self._makeRequestBody('echo', 'hello')

        gw.getResponse = lambda *args, **kwargs: self._raiseException(KeyboardInterrupt, *args, **kwargs)
        self.assertRaises(KeyboardInterrupt, self.doRequest, request, gw)

    def test_expected_exception_encode(self):
        self.old_method = remoting.encode
        try:
            gw = self._makeOne()
            gw.debug = True
            request = self._makeRequestBody('echo', 'hello')
            remoting.encode = lambda *args, **kwargs: self._raiseException(KeyboardInterrupt, *args, **kwargs)
            response = self.doRequest(request, gw)
            self.assertEqual(response.status_int, 500)
            assert 'unable to be encoded' in response.detail
            assert 'Traceback' in response.detail
        finally:
            self._restoreEncode()

    def test_expose_request(self):
        gw = self._makeOne()
        gw.expose_request = True

        executed = []

        def echo(http_request, data):
            assert hasattr(http_request, 'amf_request')
            request = http_request.amf_request

            self.assertTrue(isinstance(request, remoting.Request))

            self.assertEqual(request.target, 'echo')
            self.assertEqual(request.body, ['hello'])
            executed.append(True)

        gw.addService(echo)
        self.doRequest(self._makeRequestBody('echo', 'hello'), gw)
        assert len(executed) > 0

    def test_expected_exception_echo(self):
        gw = self._makeOne()
        gw.expose_request = True
        gw.debug = True
        gw.getResponse = lambda *args, **kwargs: self._raiseException(Exception, *args, **kwargs)
        response = self.doRequest(self._makeRequestBody('echo', 'hello'), gw)
        self.assertEqual(response.status_int, 500)
        assert 'Traceback' in response.detail

    def test_timezone(self):
        import datetime

        gw = self._makeOne()
        gw.expose_request = False
        td = datetime.timedelta(hours=-5)
        now = datetime.datetime.utcnow()

        def echo(d):
            self.assertEqual(d, now + td)
            return d

        gw.addService(echo)
        gw.timezone_offset = -18000

        response = self.doRequest(self._makeRequestBody('echo', now), gw)
        envelope = remoting.decode(response.body)
        message = envelope['/1']
        self.assertEqual(message.body, now)
