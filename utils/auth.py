import hashlib

def hash_password(password: str) -> str:
    """Hashes passwords using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()