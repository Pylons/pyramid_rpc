from pyramid_rpc.jsonrpc import jsonrpc_method

def basic(request):
    return 'basic'

@jsonrpc_method(method='exc', endpoint='api')
def exc_view(request):
    raise Exception()

@jsonrpc_method(method='create', endpoint='api')
def create_view(request, a, b):
    return {'create': 'bob'}

class JSONRPCHandler(object):
    def __init__(self, request):
        self.request = request

    @jsonrpc_method(endpoint='api')
    def say_hello(self, name):
        return 'hello, ' + name

@jsonrpc_method(endpoint='secure_api', permission='view')
def secure_hello(request, name):
    return 'hello, ' + name

@jsonrpc_method(endpoint='secure_api', permission='echo')
def secure_echo(request, msg):
    return msg
