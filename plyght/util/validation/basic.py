def validate_int(value) -> int:
    """
    Basic type check for value to determine if a value is an integer.

    :param value: Any value to be validated
    :return: The input value if valid.
    """
    if not isinstance(value, int):
        try:
            value = int(value)
        except ValueError:
            raise ValueError("Value must be an integer")
    return value


def validate_float(value) -> float:
    """
    Basic type check for value to determine if a value is a float.

    :param value: Any value to be validated
    :return: The input value if valid.
    """
    if not isinstance(value, float):
        try:
            value = float(value)
        except ValueError:
            raise ValueError("Value must be a float")
    return value


def validate_positive_int(value) -> int:
    """
    Basic type check for value to determine if a value is a positive integer.

    :param value: Any value to be validated
    :return: The input value if valid.
    """
    value = validate_int(value)
    if value <= 0:
        raise ValueError("Value must be a positive integer")
    return value


def validate_positive_float(value) -> float:
    """
    Basic type check for value to determine if a value is a positive float.

    :param value: Any value to be validated
    :return: The input value if valid.
    """
    value = validate_float(value)
    if value <= 0:
        raise ValueError("Value must be a positive float")
    return value
