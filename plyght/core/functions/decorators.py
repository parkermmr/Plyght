from functools import wraps
import inspect
import warnings

STRING_TYPES = (type(b''), type(u''))


def invoke(*dargs, **dkwargs):
    """
    This is a decorator that results in the immediate invocation
    of the decorated function. The decorator args and kwargs will
    be passed to the function. Else the decorator can just be called
    without arguments if the function does not require them.
    """
    if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
        func = dargs[0]
        func()
        return func

    def decorator(func):
        func(*dargs, **dkwargs)
        return func

    return decorator


def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used. The decorator can either recieve
    a string reason and that be conveyed, or just a regular deprecation
    warning.

    This functionality is outlined as part of PEP 702 as implementation
    in the Python standard lib: 'warnings'.
    """

    if isinstance(reason, STRING_TYPES):

        def decorator(func1):

            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter('always', DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2
                )
                warnings.simplefilter('default', DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2
            )
            warnings.simplefilter('default', DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))
