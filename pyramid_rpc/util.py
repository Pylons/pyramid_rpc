# stole from pyramid 1.4
def combine(*decorators):
    def decorated(view_callable):
        # reversed() is allows a more natural ordering in the api
        for decorator in reversed(decorators):
            view_callable = decorator(view_callable)
        return view_callable
    return decorated
