import numpy as np
from PIL import Image

from crypto_engine import aes_engine

MAGIC = b"ELSB"
HEADER_BITS = 64


def capacity_bytes(path: str) -> int:
    w, h = Image.open(path).size
    return (w * h * 3 - HEADER_BITS) // 8


def embed(cover_path: str, out_path: str, message: str, key: bytes | None = None) -> None:
    """LSB pada 3 kanal RGB. Paket: MAGIC(4) | panjang(4, big-endian) | payload."""
    payload = message.encode("utf-8")
    if key:
        payload = aes_engine.encrypt(payload, key)
    packet = MAGIC + len(payload).to_bytes(4, "big") + payload
    arr = np.array(Image.open(cover_path).convert("RGB"), dtype=np.uint8)
    flat = arr.reshape(-1)
    bits = np.unpackbits(np.frombuffer(packet, dtype=np.uint8))
    if bits.size > flat.size:
        raise ValueError(f"Pesan terlalu besar. Kapasitas gambar {(flat.size - HEADER_BITS) // 8} byte")
    flat[:bits.size] = (flat[:bits.size] & 0xFE) | bits
    Image.fromarray(flat.reshape(arr.shape)).save(out_path, format="PNG")


def extract(stego_path: str, key: bytes | None = None) -> str:
    flat = np.array(Image.open(stego_path).convert("RGB"), dtype=np.uint8).reshape(-1)
    header = np.packbits(flat[:HEADER_BITS] & 1).tobytes()
    if header[:4] != MAGIC:
        raise ValueError("Tidak ditemukan pesan tersembunyi pada gambar ini")
    n = int.from_bytes(header[4:8], "big")
    if HEADER_BITS + n * 8 > flat.size:
        raise ValueError("Header steganografi rusak")
    payload = np.packbits(flat[HEADER_BITS:HEADER_BITS + n * 8] & 1).tobytes()
    if key:
        payload = aes_engine.decrypt(payload, key)
    return payload.decode("utf-8")
