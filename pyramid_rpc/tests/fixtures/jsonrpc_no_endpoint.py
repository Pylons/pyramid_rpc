from pyramid_rpc.jsonrpc import jsonrpc_method

@jsonrpc_method(method='create')
def create_view(request):
    return {'create': 'bob'}
