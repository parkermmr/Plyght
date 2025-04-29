from pydantic import BaseModel
from typing import get_origin, get_args
from typing import Iterator, Type


def model_to_declarative_dict(model: BaseModel) -> dict:
    """
    Turns a pydantic model into a declarative typed dictionary.

    :param model: The pydantic @BaseModel to convert to a model dict.
    :return: Typed dictionary of model.
    """
    def get_field_type(field_annotation):
        """
        Validate and returns the field type annotation from a model field.

        :param field_annotation: The type annotation to validate.
        :return: The type annotation.
        """
        origin = get_origin(field_annotation)
        if origin is not None:
            args = get_args(field_annotation)
            non_none_args = [arg for arg in args if arg is not type(None)]
            return non_none_args[0] if non_none_args else field_annotation
        return field_annotation

    declarative_dict = {
        field_name: get_field_type(field_info.annotation)
        for field_name, field_info in model.__pydantic_fields__.items()
        if field_info.default is None or field_info.default_factory is None
    }

    return declarative_dict


def required_fields(
        model: Type[BaseModel],
        recursive: bool = False
        ) -> Iterator[str]:
    """
    Extracts the required fields from a model of depth >=1.

    :param model: The @BaseModel to analyse.
    :param recursive: Declare whether the model has multilayer models.

    :return: An iterator of str field names.
    """
    for name, field in model.__pydantic_fields__.items():
        if not field.is_required:
            continue
        t = field.annotation
        if recursive and isinstance(t, type) and issubclass(t, BaseModel):
            yield from required_fields(t, recursive)
        else:
            yield name
