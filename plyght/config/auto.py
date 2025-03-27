"""
Provides decorators for automatically attaching configuration classes and
for extracting caller keyword arguments. This module leverages a
CaseConverter for dynamically resolving configuration class names.
"""

import importlib
import inspect

from plyght.util.converters.case import CaseConverter

CASE_CONVERTER = CaseConverter()


def configuration(config_type: str, module_path: str = None):
    """
    Decorator that attaches a configuration class to the decorated class
    at runtime. The configuration class name is derived from the provided
    config_type by converting it to PascalCase. By default, the configuration
    class is searched for in the same module as the decorated class, but
    an alternate module may be specified.

    :param config_type: Identifies the configuration type as a string.
    :param module_path: Optional module path to import the configuration class from.
    :return: Decorator function.
    """

    def decorator(cls):
        config_class_name = CASE_CONVERTER.pascal(config_type)
        try:
            mod = (
                importlib.import_module(module_path)
                if module_path
                else importlib.import_module(cls.__module__)
            )
            config_class = getattr(mod, config_class_name)
        except (ModuleNotFoundError, AttributeError) as e:
            msg = (
                f"Configuration class '{config_class_name}' not found in module "
                f"'{module_path or cls.__module__}'"
            )
            raise ImportError(msg) from e
        cls._config = config_class()
        return cls

    return decorator


def get_kwargs():
    """
    Inspect the caller's local variables, excluding 'self' and '__class__',
    and flatten any 'kwargs' dictionary into top-level items. Returns a
    dictionary of these flattened parameters.

    :return: Dictionary of caller's local variables, merged with kwargs.
    """
    frame = inspect.currentframe().f_back
    local_vars = frame.f_locals.copy()
    local_vars.pop("self", None)
    local_vars.pop("__class__", None)

    if "kwargs" in local_vars:
        kw = local_vars.pop("kwargs")
        for k, v in kw.items():
            local_vars[k] = v

    return local_vars
