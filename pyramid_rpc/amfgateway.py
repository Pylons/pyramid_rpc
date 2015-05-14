"""Pyramid View Gateway implementation.

A :class:`~pyramid_rpc.amfgateway.PyramidGateway` instance implements a
Pyramid view compatible callable object, allowing it to be configured like any
other Pyramid view.

"""
import pyamf
from pyamf import remoting
from pyamf.remoting import gateway

from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPMethodNotAllowed,
)
from pyramid.response import Response


class PyramidGateway(gateway.BaseGateway):
    """Pyramid View Remoting Gateway

    :param expose_request:
        Defaults to True. Whether or not the service function should be
        called with the Pyramid request object.
    :param debug: Boolean toggling debug mode.

    """

    def __init__(self, *args, **kwargs):
        kwargs['expose_request'] = kwargs.get('expose_request', True)
        gateway.BaseGateway.__init__(self, *args, **kwargs)

    def getResponse(self, request, amf_request):
        """Process the AMF request, returning an AMF response"""
        response = remoting.Envelope(amf_request.amfVersion)

        for name, message in amf_request:
            request.amf_request = message

            processor = self.getProcessor(message)
            response[name] = processor(message, http_request=request)
        return response

    def __call__(self, request):
        """Processes and dispatches the request"""
        if request.method != 'POST':
            return HTTPMethodNotAllowed(['POST'])

        body = request.body
        stream = None
        timezone_offset = self._get_timezone_offset()

        # Decode the request
        try:
            amf_request = remoting.decode(body, strict=self.strict,
                                          logger=self.logger,
                                          timezone_offset=timezone_offset)
        except (pyamf.DecodeError, IOError):
            if self.logger:
                self.logger.exception('Error decoding AMF request')

            response = "400 Bad Request\n\nThe request body was unable to " \
                "be successfully decoded."

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()
            return HTTPBadRequest(detail=response)
        except Exception:
            if self.logger:
                self.logger.exception('Unexpected error decoding AMF request')

            response = ("500 Internal Server Error\n\nAn unexpected error "
                "occurred whilst decoding.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()
            return HTTPInternalServerError(detail=response)

        if self.logger:
            self.logger.debug("AMF Request: %r" % amf_request)

        # Process the request
        try:
            response = self.getResponse(request, amf_request)
        except Exception:
            if self.logger:
                self.logger.exception('Error processing AMF request')

            response = ("500 Internal Server Error\n\nThe request was "
                "unable to be successfully processed.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            return HTTPInternalServerError(detail=response)

        if self.logger:
            self.logger.debug("AMF Response: %r" % response)

        # Encode the response
        try:
            stream = remoting.encode(response, strict=self.strict,
                timezone_offset=timezone_offset)
        except:
            if self.logger:
                self.logger.exception('Error encoding AMF request')

            response = ("500 Internal Server Error\n\nThe request was "
                "unable to be encoded.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            return HTTPInternalServerError(detail=response)

        buf = stream.getvalue()

        http_response = Response(content_type=remoting.CONTENT_TYPE)
        http_response.headers['Server'] = gateway.SERVER_NAME
        http_response.write(buf)
        return http_response
