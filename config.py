from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VAULT_DIR = DATA_DIR / "vault"
STEGO_DIR = DATA_DIR / "stego"
DB_PATH = DATA_DIR / "evidencelock.db"

POW_DIFFICULTY = 4
PBKDF2_ITERATIONS = 600_000
FACE_SIZE = 66
FACE_THRESHOLD = 0.74
MIN_PASSWORD_LEN = 8

for _d in (DATA_DIR, VAULT_DIR, STEGO_DIR):
    _d.mkdir(parents=True, exist_ok=True)
