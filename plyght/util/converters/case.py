"""
A module providing case detection and transformations for string values, including:
- Snake case (snake_case)
- Pascal case (PascalCase)
- Camel case (camelCase)
- Screaming case (SCREAMING_SNAKE_CASE)
- Kebab case (kebab-case)
- Train case (Train-Case)
"""

from enum import Enum


class Case(Enum):
    """
    Enumeration of supported string cases.
    """

    SNAKE = "snake"
    PASCAL = "pascal"
    CAMEL = "camel"
    SCREAMING = "screaming"
    KEBAB = "kebab"
    TRAIN = "train"
    UNKNOWN = "unknown"


def _validate_input(value: str) -> None:
    """
    Validate the input string to ensure it is a non-empty string.
    """
    if not isinstance(value, str):
        raise TypeError("Input must be a string.")
    if not value.strip():
        raise ValueError("Input string cannot be empty or only whitespace.")


def _split_into_words(text: str) -> list[str]:
    """
    Split a string into a list of lowercase words. Splits on underscores, dashes,
    and transitions from lowercase to uppercase. Returns words in lowercase.
    """
    _validate_input(text)
    words = []
    partial = ""

    for i, ch in enumerate(text):
        if ch in ("_", "-"):
            if partial:
                words.append(partial.lower())
                partial = ""
            continue
        if i > 0 and ch.isupper() and not text[i - 1].isupper():
            if partial:
                words.append(partial.lower())
            partial = ch
        else:
            partial += ch
    if partial:
        words.append(partial.lower())

    return [w for w in words if w]


def _is_all_lower_ignoring_delims(text: str) -> bool:
    """
    Check if all letters in the text are lowercase, ignoring underscores and dashes.
    """
    return all(ch.islower() for ch in text if ch not in ("_", "-"))


def _is_title_case_ignoring_delims(text: str) -> bool:
    """
    Check if the text is in title case when ignoring underscores and dashes.
    E.g. "Train-Case" => True, "Train-case" => False.
    """
    segments = [seg for seg in text.split("-") if seg.strip()]
    if not segments:
        return False
    for seg in segments:
        if not seg:  # might be a double dash or something unexpected
            return False
        if not (seg[0].isupper() and seg[1:].islower()):
            return False
    return True


class CaseConverter:
    """
    Detects a string's case and converts it among various forms.
    """

    def __init__(self) -> None:
        """
        Initialize the CaseConverter without any state.
        """
        return

    @staticmethod
    def case(value: str) -> Case:
        """
        Detect the case of the given string.

        :param value: The input string to examine.
        :return: A Case enum value indicating the detected case.
        """
        _validate_input(value)

        if "_" in value:
            if value.isupper():
                return Case.SCREAMING
            return Case.SNAKE

        if "-" in value:
            if _is_all_lower_ignoring_delims(value):
                return Case.KEBAB
            if _is_title_case_ignoring_delims(value):
                return Case.TRAIN
            return Case.UNKNOWN

        if value and value[0].isupper():
            return Case.PASCAL
        if value and value[0].islower():
            return Case.CAMEL
        return Case.UNKNOWN

    @staticmethod
    def normalize(value: str) -> str:
        """
        Convert string to a normalized form (lower_snake_case).

        :param value: The input string to normalize.
        :return: A lower_snake_case string.
        """
        words = _split_into_words(value)
        return "_".join(words)

    @staticmethod
    def snake(value: str) -> str:
        """
        Convert string to snake_case.

        :param value: The input string to convert.
        :return: A snake_case string.
        """
        words = _split_into_words(value)
        return "_".join(words)

    @staticmethod
    def pascal(value: str) -> str:
        """
        Convert string to PascalCase.

        :param value: The input string to convert.
        :return: A PascalCase string.
        """
        words = _split_into_words(value)
        return "".join(w.capitalize() for w in words)

    @staticmethod
    def camel(value: str) -> str:
        """
        Convert string to camelCase.

        :param value: The input string to convert.
        :return: A camelCase string.
        """
        words = _split_into_words(value)
        if not words:
            return ""
        return words[0] + "".join(w.capitalize() for w in words[1:])

    @staticmethod
    def screaming(value: str) -> str:
        """
        Convert string to SCREAMING_SNAKE_CASE.

        :param value: The input string to convert.
        :return: A SCREAMING_SNAKE_CASE string.
        """
        words = _split_into_words(value)
        return "_".join(w.upper() for w in words)

    @staticmethod
    def kebab(value: str) -> str:
        """
        Convert string to kebab-case.

        :param value: The input string to convert.
        :return: A kebab-case string.
        """
        words = _split_into_words(value)
        return "-".join(words)

    @staticmethod
    def train(value: str) -> str:
        """
        Convert string to Train-Case.

        :param value: The input string to convert.
        :return: A Train-Case string.
        """
        words = _split_into_words(value)
        return "-".join(w.capitalize() for w in words)
