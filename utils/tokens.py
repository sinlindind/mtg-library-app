import uuid
from datetime import datetime, timedelta

def generate_verification_token() -> tuple[str, str]:
    """Generates a secure verification token and an expiration timestamp."""
    token = str(uuid.uuid4())
    expiration = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    return token, expiration