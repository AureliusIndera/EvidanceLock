def _shift(data: bytes, key: bytes, sign: int) -> bytes:
    if not key:
        raise ValueError("Kunci Vigenere tidak boleh kosong")
    kl = len(key)
    return bytes((b + sign * key[i % kl]) % 256 for i, b in enumerate(data))


def encrypt(data: bytes, key: bytes) -> bytes:
    """C_i = (P_i + K_(i mod m)) mod 256  (Vigenere atas alfabet 256 byte)."""
    return _shift(data, key, 1)


def decrypt(data: bytes, key: bytes) -> bytes:
    """P_i = (C_i - K_(i mod m)) mod 256."""
    return _shift(data, key, -1)
