import hashlib
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from config import STEGO_DIR, VAULT_DIR
from crypto_engine import file_cipher, super_encryption
from stego import lsb
from ui.context import parse_id


def _thumb(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((300, 220))
    return ctk.CTkImage(im, size=im.size)


class InputView(ctk.CTkFrame):
    def __init__(self, master, ctx):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.file_path = self.cover_path = None
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=4)
        ctk.CTkLabel(head, text="Perkara:").pack(side="left", padx=6)
        self.case_var = ctk.StringVar(value="(belum ada perkara)")
        self.case_menu = ctk.CTkOptionMenu(head, variable=self.case_var, values=["(belum ada perkara)"], width=480)
        self.case_menu.pack(side="left")
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True)
        self._bap(tabs.add("BAP Super Enkripsi"))
        self._file(tabs.add("File Encryptor"))
        self._stego(tabs.add("LSB Steganografi"))

    def refresh(self):
        opts = self.ctx.case_options() or ["(belum ada perkara)"]
        self.case_menu.configure(values=opts)
        if self.case_var.get() not in opts:
            self.case_var.set(opts[0])

    def _case_id(self):
        cid = parse_id(self.case_var.get())
        if cid is None:
            messagebox.showwarning("Perkara", "Buat perkara terlebih dahulu di Dashboard")
        return cid

    # ---- BAP ----
    def _bap(self, tab):
        self.bap_title = ctk.CTkEntry(tab, placeholder_text="Judul BAP / catatan", width=520)
        self.bap_title.pack(anchor="w", pady=4)
        self.bap_wit = ctk.CTkEntry(tab, placeholder_text="Nama saksi (dienkripsi di kolom DB)", width=520)
        self.bap_wit.pack(anchor="w", pady=4)
        self.bap_id = ctk.CTkEntry(tab, placeholder_text="Identitas sensitif (dienkripsi di kolom DB)", width=520)
        self.bap_id.pack(anchor="w", pady=4)
        self.bap_text = ctk.CTkTextbox(tab, height=150)
        self.bap_text.pack(fill="x", pady=4)
        ctk.CTkButton(tab, text="Super Enkripsi (Vigenere + AES-256-CBC) & Simpan", command=self._save_bap).pack(anchor="w", pady=4)
        ctk.CTkLabel(tab, text="Ciphertext tersimpan:", text_color="gray").pack(anchor="w")
        self.bap_out = ctk.CTkTextbox(tab, height=90)
        self.bap_out.pack(fill="x")

    def _save_bap(self):
        cid = self._case_id()
        title, wit = self.bap_title.get().strip(), self.bap_wit.get().strip()
        ident, text = self.bap_id.get().strip(), self.bap_text.get("1.0", "end").strip()
        if cid is None:
            return
        if not (title and wit and text):
            return messagebox.showwarning("BAP", "Judul, nama saksi, dan isi BAP wajib diisi")
        token = super_encryption.encrypt_text(text, self.ctx.keyring)
        eid, blk = self.ctx.save_evidence(cid, "BAP", title, witness_name=wit, sensitive_identity=ident or None,
                                          bap_cipher=token, file_sha256=hashlib.sha256(token.encode()).hexdigest())
        self.bap_out.delete("1.0", "end")
        self.bap_out.insert("1.0", token)
        self.bap_text.delete("1.0", "end")
        messagebox.showinfo("BAP", f"Tersimpan sebagai bukti #{eid}, blok #{blk.index}")

    # ---- File ----
    def _file(self, tab):
        self.file_title = ctk.CTkEntry(tab, placeholder_text="Judul bukti", width=520)
        self.file_title.pack(anchor="w", pady=4)
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(anchor="w", pady=4)
        ctk.CTkButton(row, text="Pilih Berkas (.pdf/.docx/.wav)", command=self._pick_file).pack(side="left")
        self.file_lbl = ctk.CTkLabel(row, text="  belum dipilih", text_color="gray")
        self.file_lbl.pack(side="left")
        ctk.CTkButton(tab, text="Enkripsi ChaCha20-Poly1305 & Simpan ke Vault", command=self._save_file).pack(anchor="w", pady=8)
        self.file_out = ctk.CTkTextbox(tab, height=140)
        self.file_out.pack(fill="x")

    def _pick_file(self):
        p = filedialog.askopenfilename(filetypes=[("Bukti", "*.pdf *.docx *.wav"), ("Semua", "*.*")])
        if p:
            self.file_path = p
            self.file_lbl.configure(text="  " + Path(p).name, text_color="white")

    def _save_file(self):
        cid = self._case_id()
        title = self.file_title.get().strip()
        if cid is None:
            return
        if not (self.file_path and title):
            return messagebox.showwarning("Berkas", "Judul dan berkas wajib diisi")
        data = Path(self.file_path).read_bytes()
        digest = file_cipher.sha256_hex(data)
        dst = VAULT_DIR / f"{uuid.uuid4().hex}.elk"
        dst.write_bytes(file_cipher.encrypt_bytes(data, self.ctx.keyring["file"]))
        eid, blk = self.ctx.save_evidence(cid, "FILE", title, file_name=Path(self.file_path).name,
                                          vault_path=str(dst), file_sha256=digest)
        self.file_out.delete("1.0", "end")
        self.file_out.insert("1.0", f"Bukti #{eid} | Blok #{blk.index}\nVault : {dst}\nSHA-256 asli: {digest}\n")

    # ---- Stego ----
    def _stego(self, tab):
        self.st_title = ctk.CTkEntry(tab, placeholder_text="Judul bukti", width=520)
        self.st_title.pack(anchor="w", pady=4)
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(anchor="w", pady=4)
        ctk.CTkButton(row, text="Pilih Gambar Cover PNG", command=self._pick_cover).pack(side="left")
        self.cover_lbl = ctk.CTkLabel(row, text="  belum dipilih", text_color="gray")
        self.cover_lbl.pack(side="left")
        self.st_msg = ctk.CTkTextbox(tab, height=80)
        self.st_msg.pack(fill="x", pady=4)
        ctk.CTkButton(tab, text="Sisipkan LSB & Simpan", command=self._save_stego).pack(anchor="w", pady=4)
        previews = ctk.CTkFrame(tab, fg_color="transparent")
        previews.pack(fill="both", expand=True)
        self.prev_cover = ctk.CTkLabel(previews, text="Cover")
        self.prev_cover.pack(side="left", padx=10)
        self.prev_stego = ctk.CTkLabel(previews, text="Stego")
        self.prev_stego.pack(side="left", padx=10)

    def _pick_cover(self):
        p = filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
        if p:
            self.cover_path = p
            self.cover_lbl.configure(text=f"  {Path(p).name} (kapasitas {lsb.capacity_bytes(p)} byte)", text_color="white")
            img = _thumb(p)
            self.prev_cover.configure(image=img, text="")
            self.prev_cover.image = img

    def _save_stego(self):
        cid = self._case_id()
        title, msg = self.st_title.get().strip(), self.st_msg.get("1.0", "end").strip()
        if cid is None:
            return
        if not (self.cover_path and title and msg):
            return messagebox.showwarning("Stego", "Judul, gambar cover, dan pesan wajib diisi")
        out = STEGO_DIR / f"{uuid.uuid4().hex}.png"
        try:
            lsb.embed(self.cover_path, str(out), msg, self.ctx.keyring["stego"])
        except ValueError as e:
            return messagebox.showerror("Stego", str(e))
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        eid, blk = self.ctx.save_evidence(cid, "STEGO", title, stego_path=str(out), file_sha256=digest)
        img = _thumb(str(out))
        self.prev_stego.configure(image=img, text="")
        self.prev_stego.image = img
        self.st_msg.delete("1.0", "end")
        messagebox.showinfo("Stego", f"Tersimpan sebagai bukti #{eid}, blok #{blk.index}")
