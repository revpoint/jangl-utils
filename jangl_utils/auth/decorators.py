from functools import wraps

from django.utils.decorators import available_attrs


def no_auth_cache(view_func):
    """
    Marks a view function as being exempt from using auth cache.
    """
    # We could just do view_func.no_auth_cache = True, but decorators
    # are nicer if they don't have side-effects, so we return a new
    # function.
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)
    wrapped_view.no_auth_cache = True
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)
