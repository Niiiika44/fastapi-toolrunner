from app.auth.hash_utils import get_password_hash, verify_password

PASSWORD = "test_password"


def test_hash_type():
    hashed_password = get_password_hash(PASSWORD)
    assert isinstance(hashed_password, str)


def test_correct_password():
    hashed_password = get_password_hash(PASSWORD)
    assert verify_password(PASSWORD, hashed_password)


def test_wrong_password():
    hashed_password = get_password_hash(PASSWORD)
    assert not verify_password("another_password", hashed_password)


def test_salt_produces_different_hashes():
    assert get_password_hash(PASSWORD) != get_password_hash(PASSWORD)
