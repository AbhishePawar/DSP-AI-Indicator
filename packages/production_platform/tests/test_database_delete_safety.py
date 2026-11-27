"""Regression tests for conditional deletion and literal preservation."""

import pytest

from production_platform.production.database import InMemoryDatabasePort
from production_platform.production.exceptions import ProviderError


def make_db():
    db = InMemoryDatabasePort()
    db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT, name TEXT)")
    db.execute("INSERT INTO users (id, name) VALUES ('a', 'Alice')")
    db.execute("INSERT INTO users (id, name) VALUES ('b', 'Bob')")
    return db


def test_conditional_delete_preserves_other_rows():
    db = make_db()
    db.execute("DELETE FROM users WHERE id = 'a'")
    assert db.fetchall("SELECT * FROM users") == [
        {"id": "b", "name": "Bob"}
    ]


def test_missing_id_preserves_all_rows():
    db = make_db()
    db.execute("DELETE FROM users WHERE id = 'missing'")
    assert len(db.fetchall("SELECT * FROM users")) == 2


def test_unconditional_delete_remains_supported():
    db = make_db()
    db.execute("DELETE FROM users")
    assert db.fetchall("SELECT * FROM users") == []


@pytest.mark.parametrize("statement", [
    "DELETE FROM users WHERE id = 'a' OR id = 'b'",
    "DELETE FROM users WHERE id != 'a'",
    "DELETE FROM users WHERE",
    "DELETE FROM users WHERE id = %s",
])
def test_unsupported_delete_never_clears_table(statement):
    db = make_db()
    with pytest.raises(ProviderError):
        db.execute(statement)
    assert len(db.fetchall("SELECT * FROM users")) == 2


def test_escaped_apostrophe_and_whitespace():
    db = make_db()
    db.execute(
        "INSERT INTO users (id, name) VALUES ('o''neil', 'Two  Spaces')"
    )
    rows = db.fetchall("SELECT * FROM users")
    assert rows[-1]["name"] == "Two  Spaces"
    db.execute("DELETE FROM users WHERE id = 'o''neil'")
    assert len(db.fetchall("SELECT * FROM users")) == 2


def test_transaction_rollback_restores_deleted_row():
    db = make_db()
    with pytest.raises(RuntimeError):
        with db.transaction() as txn:
            txn.execute("DELETE FROM users WHERE id = 'a'")
            raise RuntimeError("rollback")
    assert len(db.fetchall("SELECT * FROM users")) == 2
