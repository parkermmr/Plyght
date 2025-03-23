import importlib

from util.converters.case import snake_to_pascal


def configuration(config_type: str, module_path: str = None):
    def decorator(cls):
        config_class_name = snake_to_pascal(config_type)
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
