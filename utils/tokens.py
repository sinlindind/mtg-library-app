from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import streamlit as st

def get_serializer() -> URLSafeTimedSerializer:
    # Uses a secret key set in your secrets.toml or falls back to a default
    secret = st.secrets.get("SUPABASE_KEY", "fallback-secret-key-change-me")
    return URLSafeTimedSerializer(secret)

def generate_verification_token(email: str) -> str:
    """Generates a secure, signed token containing the user's email."""
    serializer = get_serializer()
    return serializer.dumps(email, salt="email-verify")

def verify_token(token: str, max_age: int = 86400) -> str | None:
    """
    Verifies a token and returns the email if valid.
    Default max_age is 86400 seconds (24 hours).
    Returns None if expired or invalid.
    """
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt="email-verify", max_age=max_age)
        return email
    except (SignatureExpired, BadTimeSignature):
        return None