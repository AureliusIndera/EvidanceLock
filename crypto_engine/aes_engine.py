import hashlib
import hmac

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


def _mac_key(key: bytes) -> bytes:
    return hashlib.sha256(b"EvidenceLock-MAC|" + key).digest()


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-256-CBC + PKCS7, format: IV(16) | CT | HMAC-SHA256(32) (encrypt-then-MAC)."""
    iv = get_random_bytes(16)
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext, AES.block_size))
    tag = hmac.new(_mac_key(key), iv + ct, hashlib.sha256).digest()
    return iv + ct + tag


def decrypt(blob: bytes, key: bytes) -> bytes:
    if len(blob) < 64 or (len(blob) - 48) % 16 != 0:
        raise ValueError("Ciphertext tidak valid")
    iv, ct, tag = blob[:16], blob[16:-32], blob[-32:]
    expected = hmac.new(_mac_key(key), iv + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Integritas gagal: kunci salah atau data telah dimodifikasi")
    return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), AES.block_size)
