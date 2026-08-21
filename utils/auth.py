import hashlib
import os

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """
    Hashes a password with a secure random salt using SHA-256.
    Returns (hex_password, hex_salt).
    """
    if salt is None:
        salt = os.urandom(16)
    
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt, 
        100000
    )
    return pwd_hash.hex(), salt.hex()

def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Verifies a password against its stored hash and salt."""
    salt_bytes = bytes.fromhex(stored_salt)
    new_hash, _ = hash_password(password, salt_bytes)
    return new_hash == stored_hash