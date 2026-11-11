import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image

from auth.biometric import FaceEngine
from auth.password import hash_password, verify_password
from blockchain.chain import Blockchain
from crypto_engine import file_cipher, super_encryption, vigenere
from crypto_engine.keys import derive_keyring
from database.dao import Database
from stego import lsb


def main():
    kr = derive_keyring("Rahasia#2026", "ABCD-1234", os.urandom(16))

    assert vigenere.decrypt(vigenere.encrypt(b"saksi", b"KUNCI"), b"KUNCI") == b"saksi"
    token = super_encryption.encrypt_text("BAP saksi: Budi, Jl. Malioboro 1", kr)
    assert super_encryption.decrypt_text(token, kr).startswith("BAP saksi")

    blob = file_cipher.encrypt_bytes(b"%PDF-1.7 dummy", kr["file"])
    assert file_cipher.decrypt_bytes(blob, kr["file"]) == b"%PDF-1.7 dummy"
    try:
        file_cipher.decrypt_bytes(blob[:-1] + bytes([blob[-1] ^ 1]), kr["file"])
        raise SystemExit("tamper tidak terdeteksi")
    except ValueError:
        pass

    stored = hash_password("pass1234", 1000)
    assert verify_password("pass1234", stored) and not verify_password("salah", stored)

    rng = np.random.default_rng(1)
    a = FaceEngine.vector_from_gray(rng.integers(0, 255, (120, 120), dtype=np.uint8))
    b = FaceEngine.vector_from_gray(rng.integers(0, 255, (120, 120), dtype=np.uint8))
    assert abs(FaceEngine.similarity(a, a) - 1.0) < 1e-5 and FaceEngine.similarity(a, b) < 1.0

    with tempfile.TemporaryDirectory() as tmp:
        cover, out = Path(tmp) / "c.png", Path(tmp) / "s.png"
        Image.fromarray(rng.integers(0, 255, (80, 80, 3), dtype=np.uint8)).save(cover)
        lsb.embed(str(cover), str(out), "-7.7956, 110.3695 | ID-001", kr["stego"])
        assert lsb.extract(str(out), kr["stego"]) == "-7.7956, 110.3695 | ID-001"

        db = Database(Path(tmp) / "t.db")
        cid = db.add_case("001/Pid/2026", "Perkara uji")
        eid = db.add_evidence(kr["db"], cid, "BAP", "BAP 1", witness_name="Budi",
                              sensitive_identity="NIK 3404...", bap_cipher=token)
        raw = db.conn.execute("SELECT witness_name FROM evidence WHERE id=?", (eid,)).fetchone()[0]
        assert "Budi" not in raw and db.get_evidence(eid, kr["db"])["witness_name"] == "Budi"
        db.close()

    chain = Blockchain(3)
    chain.add_block({"action": "A"})
    chain.add_block({"action": "B"})
    assert chain.validate()[0]
    chain.chain[1].data["action"] = "X"
    ok, issues = chain.validate()
    assert not ok and 1 in issues
    print("SEMUA TES LULUS")


if __name__ == "__main__":
    main()
