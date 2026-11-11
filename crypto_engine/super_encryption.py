import base64

from . import aes_engine, vigenere


def encrypt_text(text: str, keyring: dict) -> str:
    """Lapis 1: Vigenere (klasik) -> Lapis 2: AES-256-CBC (modern) -> Base64."""
    stage1 = vigenere.encrypt(text.encode("utf-8"), keyring["vigenere"])
    return base64.b64encode(aes_engine.encrypt(stage1, keyring["text"])).decode("ascii")


def decrypt_text(token: str, keyring: dict) -> str:
    stage1 = aes_engine.decrypt(base64.b64decode(token), keyring["text"])
    return vigenere.decrypt(stage1, keyring["vigenere"]).decode("utf-8")
