import hashlib
import json
import time
from dataclasses import dataclass


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Block:
    index: int
    timestamp: float
    data: dict
    previous_hash: str
    nonce: int = 0
    data_hash: str = ""
    hash: str = ""

    def compute_data_hash(self) -> str:
        return sha256_hex(json.dumps(self.data, sort_keys=True, separators=(",", ":")))

    def compute_hash(self) -> str:
        return sha256_hex(f"{self.index}|{self.timestamp:.6f}|{self.data_hash}|{self.previous_hash}|{self.nonce}")

    def mine(self, difficulty: int) -> None:
        prefix = "0" * difficulty
        self.data_hash = self.compute_data_hash()
        self.nonce = 0
        digest = self.compute_hash()
        while not digest.startswith(prefix):
            self.nonce += 1
            digest = self.compute_hash()
        self.hash = digest


class Blockchain:
    def __init__(self, difficulty: int = 4, blocks: list[Block] | None = None):
        self.difficulty = difficulty
        self.chain: list[Block] = list(blocks) if blocks else []
        if not self.chain:
            genesis = Block(0, 0.0, {"action": "GENESIS"}, "0" * 64)
            genesis.mine(difficulty)
            self.chain.append(genesis)

    @property
    def last(self) -> Block:
        return self.chain[-1]

    def add_block(self, data: dict) -> Block:
        block = Block(len(self.chain), time.time(), data, self.last.hash)
        block.mine(self.difficulty)
        self.chain.append(block)
        return block

    def validate(self) -> tuple[bool, dict[int, list[str]]]:
        issues: dict[int, list[str]] = {}
        prefix = "0" * self.difficulty
        for i, b in enumerate(self.chain):
            errs = []
            if b.index != i:
                errs.append("Indeks blok tidak berurutan")
            if b.data_hash != b.compute_data_hash():
                errs.append("Data hash tidak cocok (isi data dimodifikasi)")
            if b.hash != b.compute_hash():
                errs.append("Hash blok tidak cocok")
            if not b.hash.startswith(prefix):
                errs.append("Proof-of-Work tidak valid")
            if i > 0 and b.previous_hash != self.chain[i - 1].hash:
                errs.append("Previous hash tidak cocok dengan blok sebelumnya")
            if errs:
                issues[i] = errs
        return (not issues), issues
