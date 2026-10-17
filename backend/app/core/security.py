import hashlib
import hmac
import os
from base64 import b64decode, b64encode

_ALGORITHM = "sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode(), salt, _ITERATIONS)
    return (
        f"pbkdf2_{_ALGORITHM}${_ITERATIONS}${b64encode(salt).decode()}${b64encode(digest).decode()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$")
        _, algorithm = scheme.split("_", 1)
        salt = b64decode(salt_b64)
        expected = b64decode(digest_b64)
        rounds = int(iterations)
    except ValueError, TypeError:
        return False
    candidate = hashlib.pbkdf2_hmac(algorithm, password.encode(), salt, rounds)
    return hmac.compare_digest(candidate, expected)
