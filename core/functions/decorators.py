def invoke(*dargs, **dkwargs):
    if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
        func = dargs[0]
        func()
        return func

    def decorator(func):
        func(*dargs, **dkwargs)
        return func
    return decorator
