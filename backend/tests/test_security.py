from app.core.security import hash_password, verify_password


def test_password_round_trips() -> None:
    encoded = hash_password("s3cret-password")

    assert verify_password("s3cret-password", encoded)


def test_wrong_password_is_rejected() -> None:
    encoded = hash_password("s3cret-password")

    assert not verify_password("wrong-password", encoded)


def test_malformed_hash_is_rejected() -> None:
    assert not verify_password("anything", "not-a-valid-hash")


def test_hash_is_salted() -> None:
    assert hash_password("same") != hash_password("same")
