import functools
import flask

# extracts the parameters from either request.args or request.form
# (in_ can either be 'args' or 'form'). if the parameters are not there,
# returns a 400 status code displaying the first missing parameter
def needs_parameters(*params):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            # expect parameters in either the query or form dependent
            # on the type of request being made
            d = {
                'GET': flask.request.args,
                'POST': flask.request.form
            }[flask.request.method]
            # ensure that all parameters are there and pass them on
            # to the decorated function
            try:
                kwargs.update({param: d[param] for param in params})
            except KeyError as e:
                return "missing parameter '{}'".format(e.args[0]), 400
            return f(*args, **kwargs)
        return decorated
    return decorator

# extracts the parameters from either request.args or request.form
# (in_ can either be 'args' or 'form'). missing parameters are replaced
# with None
def accepts_parameters(*params):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            # expect parameters in either the query or form dependent
            # on the type of request being made
            d = {
                'GET': flask.request.args,
                'POST': flask.request.form
            }[flask.request.method]
            # pass on the named parameters to the decorated function
            kwargs.update({param: d.get(param) for param in params})
            return f(*args, **kwargs)
        return decorated
    return decorator
