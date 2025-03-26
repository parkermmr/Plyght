import importlib
import inspect


from plyght.util.converters.case import CaseConverter

CASE_CONVERTER = CaseConverter()


def configuration(config_type: str, module_path: str = None):
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
    Use Python's inspect to get a dict of the caller's local variables.
    Flatten out any 'kwargs' so that they become top-level items.
    Returns a dictionary where keys are parameter names and values are
    whatever was passed in at call time, excluding 'self'.
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
