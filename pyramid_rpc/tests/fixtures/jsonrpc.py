from pyramid_rpc.jsonrpc import jsonrpc_method

@jsonrpc_method(method='create', endpoint='api')
def create_view(request, a, b):
    return {'create': 'bob'}
