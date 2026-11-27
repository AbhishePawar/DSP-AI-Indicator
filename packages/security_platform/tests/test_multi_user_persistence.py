"""User updates must never delete unrelated identities."""

from dataclasses import replace

from production_platform import InfrastructureBundle
from security_platform import Role, SqlUserRepository, UserRecord


def test_updating_user_preserves_other_users():
    infra = InfrastructureBundle.create_offline()
    repo = SqlUserRepository(infra.database)

    alice = UserRecord(
        user_id="usr_alice",
        username="alice",
        role=Role.CLIENT,
    )

    bob = UserRecord(
        user_id="usr_bob",
        username="bob",
        role=Role.RESEARCHER,
    )

    repo.upsert(alice)
    repo.upsert(bob)

    repo.upsert(replace(alice, failed_login_count=1))

    assert repo.get("usr_bob") == bob
    assert repo.get("usr_alice").failed_login_count == 1
    assert len(repo.list_users()) == 2

    repo.set_active("usr_alice", active=False)

    assert repo.get("usr_bob") == bob
    assert repo.get("usr_alice").active is False
    assert len(repo.list_users()) == 2

    repo.set_active("usr_alice", active=True)

    assert repo.get("usr_alice").active is True
    assert repo.get("usr_bob") == bob
