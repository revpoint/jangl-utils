from jangl_utils.auth.middleware import AuthMiddleware


def get_full_module(cls):
    return '{cls.__module__}.{cls.__name__}'.format(cls=cls)


def replace_auth_middleware(middleware, add_class, remove_class=AuthMiddleware):
    old_module = get_full_module(remove_class)
    new_module = get_full_module(add_class)
    return tuple([cls for cls in middleware if cls != old_module] + [new_module])
