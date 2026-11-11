import hashlib

from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Random import get_random_bytes

MAGIC = b"ELK1"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """ChaCha20-Poly1305 (AEAD). Format: MAGIC(4) | nonce(12) | tag(16) | ciphertext."""
    nonce = get_random_bytes(12)
    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    cipher.update(MAGIC)
    ct, tag = cipher.encrypt_and_digest(data)
    return MAGIC + nonce + tag + ct


def decrypt_bytes(blob: bytes, key: bytes) -> bytes:
    if len(blob) < 32 or blob[:4] != MAGIC:
        raise ValueError("Format berkas terenkripsi tidak valid")
    nonce, tag, ct = blob[4:16], blob[16:32], blob[32:]
    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    cipher.update(MAGIC)
    try:
        return cipher.decrypt_and_verify(ct, tag)
    except ValueError:
        raise ValueError("Autentikasi gagal: kunci salah atau berkas telah dimodifikasi")
