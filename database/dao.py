import base64
import json
import sqlite3
from datetime import datetime

from blockchain.chain import Block
from config import DB_PATH
from crypto_engine import aes_engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cases(
    id INTEGER PRIMARY KEY AUTOINCREMENT, case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence(
    id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER NOT NULL REFERENCES cases(id),
    evidence_type TEXT NOT NULL, title TEXT NOT NULL,
    witness_name TEXT, sensitive_identity TEXT, bap_cipher TEXT,
    file_name TEXT, vault_path TEXT, stego_path TEXT, file_sha256 TEXT,
    block_index INTEGER, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL,
    action TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS blocks(
    idx INTEGER PRIMARY KEY, timestamp REAL NOT NULL, data TEXT NOT NULL,
    data_hash TEXT NOT NULL, previous_hash TEXT NOT NULL, nonce INTEGER NOT NULL, hash TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _enc(value: str | None, key: bytes) -> str | None:
    if value is None:
        return None
    return base64.b64encode(aes_engine.encrypt(value.encode("utf-8"), key)).decode("ascii")


def _dec(value: str | None, key: bytes) -> str | None:
    if value is None:
        return None
    return aes_engine.decrypt(base64.b64decode(value), key).decode("utf-8")


class Database:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # settings
    def get_setting(self, key: str):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, value))
        self.conn.commit()

    # cases
    def add_case(self, case_number: str, title: str) -> int:
        cur = self.conn.execute("INSERT INTO cases(case_number, title, created_at) VALUES(?,?,?)",
                                (case_number, title, _now()))
        self.conn.commit()
        return cur.lastrowid

    def list_cases(self):
        return self.conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()

    # evidence (kolom sensitif dienkripsi AES-256-CBC sebelum INSERT)
    def add_evidence(self, db_key: bytes, case_id: int, etype: str, title: str, *,
                     witness_name=None, sensitive_identity=None, bap_cipher=None,
                     file_name=None, vault_path=None, stego_path=None, file_sha256=None) -> int:
        cur = self.conn.execute(
            "INSERT INTO evidence(case_id, evidence_type, title, witness_name, sensitive_identity, "
            "bap_cipher, file_name, vault_path, stego_path, file_sha256, created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, etype, title, _enc(witness_name, db_key), _enc(sensitive_identity, db_key),
             bap_cipher, file_name, vault_path, stego_path, file_sha256, _now()))
        self.conn.commit()
        return cur.lastrowid

    def set_block_index(self, evidence_id: int, block_index: int) -> None:
        self.conn.execute("UPDATE evidence SET block_index=? WHERE id=?", (block_index, evidence_id))
        self.conn.commit()

    def get_evidence(self, evidence_id: int, db_key: bytes) -> dict:
        row = self.conn.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        if row is None:
            raise KeyError("Bukti tidak ditemukan")
        d = dict(row)
        d["witness_name"] = _dec(d["witness_name"], db_key)
        d["sensitive_identity"] = _dec(d["sensitive_identity"], db_key)
        return d

    def list_evidence(self):
        return self.conn.execute(
            "SELECT e.id, e.evidence_type, e.title, e.created_at, c.case_number "
            "FROM evidence e JOIN cases c ON c.id = e.case_id ORDER BY e.id DESC").fetchall()

    # audit log
    def log(self, actor: str, action: str, detail: str = "") -> None:
        self.conn.execute("INSERT INTO audit_log(ts, actor, action, detail) VALUES(?,?,?,?)",
                          (_now(), actor, action, detail))
        self.conn.commit()

    def recent_logs(self, limit: int = 200):
        return self.conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def stats(self) -> dict:
        q = lambda t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        return {"cases": q("cases"), "evidence": q("evidence"), "blocks": q("blocks")}

    # blockchain persistence
    def save_block(self, b: Block) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO blocks(idx, timestamp, data, data_hash, previous_hash, nonce, hash) "
            "VALUES(?,?,?,?,?,?,?)",
            (b.index, b.timestamp, json.dumps(b.data, sort_keys=True), b.data_hash,
             b.previous_hash, b.nonce, b.hash))
        self.conn.commit()

    def load_blocks(self) -> list[Block]:
        rows = self.conn.execute("SELECT * FROM blocks ORDER BY idx").fetchall()
        return [Block(r["idx"], r["timestamp"], json.loads(r["data"]), r["previous_hash"],
                      r["nonce"], r["data_hash"], r["hash"]) for r in rows]
