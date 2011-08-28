from pyramid_rpc.jsonrpc import jsonrpc_method

@jsonrpc_method(endpoint='api')
def create(request, a, b):
    return {'create': 'bob'}
