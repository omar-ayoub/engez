import os
import base64
import logging

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from app.core.config import settings

logger = logging.getLogger(__name__)

_NONCE_SIZE = 12
_INFO_PREFIX = b"engez-credential-encryption-v1"


def _derive_company_key(company_id: str) -> bytes:
    master_key = bytes.fromhex(settings.CREDENTIAL_MASTER_KEY)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_INFO_PREFIX + company_id.encode(),
    )
    return hkdf.derive(master_key)


def encrypt(company_id: str, plaintext: str) -> str:
    key = _derive_company_key(company_id)
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(company_id: str, encrypted: str) -> str:
    key = _derive_company_key(company_id)
    raw = base64.b64decode(encrypted)
    nonce = raw[:_NONCE_SIZE]
    ciphertext = raw[_NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
