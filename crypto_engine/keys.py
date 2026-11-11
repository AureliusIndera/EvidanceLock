from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF, scrypt

LABELS = ("vigenere", "text", "file", "db", "stego")


def derive_keyring(password: str, dongle_serial: str, salt: bytes) -> dict:
    """Master key = scrypt(password | serial dongle); sub-key per modul via HKDF-SHA256."""
    master = scrypt(password.encode("utf-8") + b"|" + dongle_serial.encode("utf-8"),
                    salt, 32, N=2 ** 15, r=8, p=1)
    return {label: HKDF(master, 32, salt, SHA256, context=label.encode()) for label in LABELS}
