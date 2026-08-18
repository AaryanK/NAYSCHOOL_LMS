import pytest
import warnings
from backend.services.token_service import encrypt_token, decrypt_token, _get_fernet
from backend.config import settings

def test_encrypt_decrypt_roundtrip():
    original_token = "my-secret-access-token-12345"
    encrypted = encrypt_token(original_token)
    assert encrypted != original_token
    assert len(encrypted) > 0
    
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token

def test_fallback_encryption_with_warnings():
    # If key is None, it should raise a UserWarning about fallback
    settings.TOKEN_ENCRYPTION_KEY = None
    
    with pytest.warns(UserWarning) as record:
        _get_fernet()
    
    # Verify warning was raised
    assert any("Using SECRET_KEY-derived key as fallback" in str(r.message) for r in record)

def test_invalid_key_fallback_with_warnings():
    # An invalid base64 key or short key should trigger warning
    settings.TOKEN_ENCRYPTION_KEY = "invalid-key-not-32-bytes"
    
    with pytest.warns(UserWarning) as record:
        _get_fernet()
        
    assert any("not a valid 32-byte Fernet key" in str(r.message) for r in record)
