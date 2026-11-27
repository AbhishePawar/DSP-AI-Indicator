"""Regression tests for quoted SQL values."""

import pytest

from production_platform.production.database import (
    InMemoryDatabasePort,
    _parse_insert,
)
from production_platform.production.exceptions import ProviderError


@pytest.mark.parametrize(
    "value",
    [
        "$argon2id$v=19$m=65536,t=3,p=4$test$synth",
        "read,write,admin",
        "Pawar, Abhishek",
        "O'Brien",
        "",
        "a,b,c",
        "VALUES (a,b)",
    ],
)
def test_quoted_values_round_trip(value):
    db = InMemoryDatabasePort()
    escaped = value.replace("'", "''")

    db.execute(
        "CREATE TABLE IF NOT EXISTS records "
        "(id INTEGER, content TEXT)"
    )

    db.execute(
        f"INSERT INTO records (id, content) "
        f"VALUES (1, '{escaped}')"
    )

    assert db.fetchall("SELECT * FROM records") == [
        {"id": 1, "content": value}
    ]


def test_malformed_literal_is_rejected():
    with pytest.raises(ProviderError):
        _parse_insert(
            "INSERT INTO records (content) VALUES ('broken)"
        )


def test_column_count_mismatch_is_rejected():
    with pytest.raises(ValueError):
        _parse_insert(
            "INSERT INTO records (content) VALUES ('a', 'b')"
        )
