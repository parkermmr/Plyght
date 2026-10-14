"""
Case detection and conversion between the common identifier styles.
"""

import pytest

from plyght.util import Case, CaseConverter


@pytest.mark.parametrize(
    ("value", "case"),
    [
        ("snake_case", Case.SNAKE),
        ("SCREAMING_CASE", Case.SCREAMING),
        ("PascalCase", Case.PASCAL),
        ("camelCase", Case.CAMEL),
        ("kebab-case", Case.KEBAB),
        ("Train-Case", Case.TRAIN),
        ("Mixed-case", Case.UNKNOWN),
    ],
)
def test_detects(value, case):
    assert CaseConverter.case(value) == case


def test_converts():
    assert CaseConverter.snake("RedisConfig") == "redis_config"
    assert CaseConverter.pascal("redis_config") == "RedisConfig"
    assert CaseConverter.camel("redis-config") == "redisConfig"
    assert CaseConverter.screaming("redisConfig") == "REDIS_CONFIG"
    assert CaseConverter.kebab("RedisConfig") == "redis-config"
    assert CaseConverter.train("redis_config") == "Redis-Config"


def test_refuses_blank():
    with pytest.raises(ValueError):
        CaseConverter.snake("  ")
    with pytest.raises(TypeError):
        CaseConverter.snake(None)
