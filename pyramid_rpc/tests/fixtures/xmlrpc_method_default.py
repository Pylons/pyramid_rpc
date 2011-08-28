from pyramid_rpc.xmlrpc import xmlrpc_method

@xmlrpc_method(endpoint='api')
def create(request, a, b):
    return {'create': 'bob'}
