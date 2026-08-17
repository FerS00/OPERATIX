"""Password hashing isolated from API routes."""

from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password with the recommended Argon2 configuration."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing the stored hash to callers."""
    return _password_hash.verify(password, password_hash)
