def includeme(config):
    config.include('pyramid_rpc.jsonrpc')

    config.add_jsonrpc_endpoint('api', '/api/jsonrpc')
    config.scan('.views')
    config.add_jsonrpc_method('.views.basic', endpoint='api', method='basic')

    config.add_jsonrpc_endpoint('secure_api', '/api/jsonrpc/secure',
                                factory='.security.Root')
