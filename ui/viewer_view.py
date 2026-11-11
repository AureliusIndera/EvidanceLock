import hashlib
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from crypto_engine import file_cipher, super_encryption
from stego import lsb
from ui.context import parse_id


class ViewerView(ctk.CTkFrame):
    def __init__(self, master, ctx):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=4)
        self.ev_var = ctk.StringVar(value="(belum ada bukti)")
        self.ev_menu = ctk.CTkOptionMenu(bar, variable=self.ev_var, values=["(belum ada bukti)"], width=520)
        self.ev_menu.pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Buka / Dekripsi Bukti", command=self._open).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Ekstrak Stego dari PNG...", command=self._extract_file,
                      fg_color="#475569").pack(side="left", padx=4)
        self.out = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier", size=13))
        self.out.pack(fill="both", expand=True, pady=4)
        self.preview = ctk.CTkLabel(self, text="")
        self.preview.pack(pady=4)

    def refresh(self):
        opts = self.ctx.evidence_options() or ["(belum ada bukti)"]
        self.ev_menu.configure(values=opts)
        if self.ev_var.get() not in opts:
            self.ev_var.set(opts[0])

    def _show(self, text):
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)

    def _open(self):
        eid = parse_id(self.ev_var.get())
        if eid is None:
            return
        kr = self.ctx.keyring
        self.preview.configure(image=None, text="")
        try:
            row = self.ctx.db.get_evidence(eid, kr["db"])
            lines = [f"Bukti #{eid} [{row['evidence_type']}] {row['title']}",
                     f"Dicatat: {row['created_at']} | Blok #{row['block_index']}"]
            if row["witness_name"]:
                lines += [f"Nama saksi        : {row['witness_name']}",
                          f"Identitas sensitif: {row['sensitive_identity'] or '-'}"]
            if row["evidence_type"] == "BAP":
                lines += ["", "Isi BAP (terdekripsi):", super_encryption.decrypt_text(row["bap_cipher"], kr)]
            elif row["evidence_type"] == "FILE":
                plain = file_cipher.decrypt_bytes(Path(row["vault_path"]).read_bytes(), kr["file"])
                ok = file_cipher.sha256_hex(plain) == row["file_sha256"]
                lines += ["", f"Berkas asli: {row['file_name']}",
                          f"Integritas SHA-256: {'COCOK' if ok else 'TIDAK COCOK'}"]
                dst = filedialog.asksaveasfilename(initialfile=row["file_name"], title="Simpan berkas terdekripsi")
                if dst:
                    Path(dst).write_bytes(plain)
                    lines.append(f"Disimpan ke: {dst}")
            else:
                path = row["stego_path"]
                ok = hashlib.sha256(Path(path).read_bytes()).hexdigest() == row["file_sha256"]
                lines += ["", f"Integritas SHA-256 gambar: {'COCOK' if ok else 'TIDAK COCOK'}",
                          "Pesan tersembunyi:", lsb.extract(path, kr["stego"])]
                im = Image.open(path).convert("RGB")
                im.thumbnail((300, 200))
                img = ctk.CTkImage(im, size=im.size)
                self.preview.configure(image=img)
                self.preview.image = img
            self._show("\n".join(lines))
            self.ctx.record("EVIDENCE_ACCESSED", f"{row['evidence_type']}: {row['title']}", eid, row["file_sha256"])
        except (ValueError, FileNotFoundError, KeyError) as e:
            self._show(f"GAGAL: {e}")
            messagebox.showerror("Viewer", str(e))

    def _extract_file(self):
        p = filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
        if not p:
            return
        try:
            self._show("Pesan tersembunyi:\n" + lsb.extract(p, self.ctx.keyring["stego"]))
        except ValueError as e:
            self._show(f"GAGAL: {e}")
