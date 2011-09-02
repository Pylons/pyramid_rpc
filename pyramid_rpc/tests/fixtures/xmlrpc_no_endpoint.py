from pyramid_rpc.xmlrpc import xmlrpc_method

@xmlrpc_method(method='create')
def create_view(request):
    pass
