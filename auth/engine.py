import hashlib
import hmac
import os

from config import FACE_THRESHOLD, MIN_PASSWORD_LEN
from crypto_engine.keys import derive_keyring

from .biometric import FaceEngine, decode_vector, encode_vector
from .password import hash_password, verify_password


class AuthError(Exception):
    pass


class AuthEngine:
    def __init__(self, db):
        self.db = db

    def is_enrolled(self) -> bool:
        return self.db.get_setting("pw_hash") is not None

    @staticmethod
    def _dongle_digest(serial: str, salt: bytes) -> str:
        return hashlib.sha256(salt + serial.encode("utf-8")).hexdigest()

    def find_registered(self, dongles):
        """Kembalikan dongle terdaftar dari daftar dongle yang tercolok, atau None."""
        digest, salt_hex = self.db.get_setting("dongle_digest"), self.db.get_setting("kdf_salt")
        if not digest or not salt_hex:
            return None
        salt = bytes.fromhex(salt_hex)
        return next((d for d in dongles
                     if hmac.compare_digest(self._dongle_digest(d.serial, salt), digest)), None)

    def enroll(self, password: str, dongle, face_vec) -> dict:
        if len(password) < MIN_PASSWORD_LEN:
            raise AuthError(f"Password minimal {MIN_PASSWORD_LEN} karakter")
        salt = os.urandom(16)
        self.db.set_setting("kdf_salt", salt.hex())
        self.db.set_setting("pw_hash", hash_password(password))
        self.db.set_setting("dongle_digest", self._dongle_digest(dongle.serial, salt))
        self.db.set_setting("face_template", encode_vector(face_vec))
        self.db.log("system", "ENROLL", f"Dongle {dongle.label} dan wajah didaftarkan")
        return derive_keyring(password, dongle.serial, salt)

    def verify(self, password: str, dongles, face_vec):
        salt = bytes.fromhex(self.db.get_setting("kdf_salt"))
        match = self.find_registered(dongles)
        if match is None:
            raise AuthError("USB dongle terdaftar tidak ditemukan")
        if not verify_password(password, self.db.get_setting("pw_hash")):
            raise AuthError("Password salah")
        score = FaceEngine.similarity(decode_vector(self.db.get_setting("face_template")), face_vec)
        if score < FACE_THRESHOLD:
            raise AuthError(f"Wajah tidak cocok (skor {score:.2f} < {FACE_THRESHOLD:.2f})")
        self.db.log("user", "LOGIN", f"Login berhasil, skor wajah {score:.3f}")
        return derive_keyring(password, match.serial, salt), score