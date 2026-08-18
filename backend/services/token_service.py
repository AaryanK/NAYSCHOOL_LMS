import base64
import hashlib
import warnings
from cryptography.fernet import Fernet
from backend.config import settings

def _get_fernet() -> Fernet:
    key_str = getattr(settings, "TOKEN_ENCRYPTION_KEY", None)
    if not key_str:
        if settings.APP_ENV.lower() not in {"development", "dev", "test", "testing", "local"}:
            raise RuntimeError("TOKEN_ENCRYPTION_KEY must be configured with a valid Fernet key outside development.")
        warnings.warn("TOKEN_ENCRYPTION_KEY is not set. Using SECRET_KEY-derived key as fallback.")
        hash_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key_str = base64.urlsafe_b64encode(hash_bytes).decode()
    else:
        try:
            # Validate it's a valid Fernet key (32 bytes after base64 decoding)
            decoded = base64.urlsafe_b64decode(key_str.encode())
            if len(decoded) != 32:
                raise ValueError("Key must decode to exactly 32 bytes")
        except Exception:
            if settings.APP_ENV.lower() not in {"development", "dev", "test", "testing", "local"}:
                raise RuntimeError("TOKEN_ENCRYPTION_KEY is invalid; a valid Fernet key is required outside development.")
            warnings.warn("TOKEN_ENCRYPTION_KEY is not a valid 32-byte Fernet key. Falling back to SECRET_KEY-derived key.")
            hash_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            key_str = base64.urlsafe_b64encode(hash_bytes).decode()
            
    return Fernet(key_str.encode())

def encrypt_token(token: str) -> str:
    if not token:
        return ""
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()

def decrypt_token(token_encrypted: str) -> str:
    if not token_encrypted:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(token_encrypted.encode()).decode()
    except Exception:
        warnings.warn("Failed to decrypt stored token.")
        return ""
