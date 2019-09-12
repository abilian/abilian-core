from abilian.core.models.subjects import User


def test_non_ascii_password() -> None:
    """Ensure we can store and test non-ascii password without any
    UnicodeEncodeError."""
    user = User()

    user.set_password("Hé")

    if not isinstance(user.password, str):
        # when actually retrieved from database, it should be Unicode
        user.password = str(user.password)

    assert user.authenticate("Hé")
