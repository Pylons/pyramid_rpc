from pyramid_rpc.xmlrpc import xmlrpc_method

@xmlrpc_method(method='create', endpoint='api')
def create_view(request, a, b):
    return {'create': 'bob'}
