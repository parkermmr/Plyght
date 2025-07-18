"""
This module provides decorators for immediate function invocation and for
issuing deprecation warnings. The `invoke` decorator can call a function
immediately with given arguments, and the `deprecated` decorator marks
functions or classes as deprecated, emitting warnings when called.
"""

import inspect
import warnings
from functools import wraps

STRING_TYPES = (type(b""), type(""))


def invoke(*dargs, **dkwargs):
    """
    Decorator that immediately invokes the decorated function with the provided
    arguments. If no arguments are specified for the decorator, it simply calls
    the decorated function once. Otherwise, it calls the function using the
    given decorator arguments.

    #### Usage:

        ```
        @invoke
        def some_function():
            print("Called immediately")
        ```
        </br>
        ```
        @invoke("arg1", key="value")
        def another_function(arg1, key=None):
            print(f"{arg1}, {key}")
        ```
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
    Decorator that marks a function or class as deprecated, emitting a
    DeprecationWarning when it is called. The decorator can accept either
    a string providing the reason for deprecation, or be applied directly
    to a function or class.

    #### Usage:
        ```
        @deprecated("Use the new_function instead.")
        def old_function():
            pass
        ```
        </br>
        ```
        @deprecated
        def another_old_function():
            pass
        ```

    :param reason: Either a string describing why the entity is deprecated,
                   or the function/class being marked as deprecated.
    :raises TypeError: If 'reason' is not a string, function, or class.
    """
    if isinstance(reason, STRING_TYPES):

        def decorator(func1):
            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter("always", DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                warnings.simplefilter("default", DeprecationWarning)
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
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))
