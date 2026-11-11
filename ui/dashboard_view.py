import sqlite3
from tkinter import messagebox

import customtkinter as ctk


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, ctx):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", pady=(4, 10))
        self.values = {}
        for i, (key, title) in enumerate([("cases", "Perkara"), ("evidence", "Bukti Digital"),
                                          ("blocks", "Blok Rantai"), ("chain", "Status Rantai")]):
            stats.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(stats)
            card.grid(row=0, column=i, padx=6, sticky="ew")
            lbl = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=30, weight="bold"))
            lbl.pack(pady=(14, 0))
            ctk.CTkLabel(card, text=title, text_color="gray").pack(pady=(0, 12))
            self.values[key] = lbl

        form = ctk.CTkFrame(self)
        form.pack(fill="x", pady=6)
        self.case_no = ctk.CTkEntry(form, placeholder_text="No. Perkara (mis. 123/Pid.B/2026/PN Smn)", width=330)
        self.case_no.pack(side="left", padx=10, pady=10)
        self.case_title = ctk.CTkEntry(form, placeholder_text="Judul perkara", width=330)
        self.case_title.pack(side="left", padx=4)
        ctk.CTkButton(form, text="Tambah Perkara", command=self._add_case).pack(side="left", padx=10)

        ctk.CTkLabel(self, text="Audit Trail Log", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(8, 2))
        self.log = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier", size=12))
        self.log.pack(fill="both", expand=True)

    def _add_case(self):
        no, title = self.case_no.get().strip(), self.case_title.get().strip()
        if not no or not title:
            return messagebox.showwarning("Perkara", "Nomor dan judul perkara wajib diisi")
        try:
            self.ctx.db.add_case(no, title)
        except sqlite3.IntegrityError:
            return messagebox.showerror("Perkara", "Nomor perkara sudah terdaftar")
        self.ctx.record("CASE_CREATED", f"{no} - {title}")
        self.case_no.delete(0, "end")
        self.case_title.delete(0, "end")
        self.refresh()

    def refresh(self):
        s = self.ctx.db.stats()
        valid, _ = self.ctx.chain.validate()
        self.values["cases"].configure(text=str(s["cases"]))
        self.values["evidence"].configure(text=str(s["evidence"]))
        self.values["blocks"].configure(text=str(len(self.ctx.chain.chain)))
        self.values["chain"].configure(text="VALID" if valid else "RUSAK",
                                       text_color="#4ade80" if valid else "#f87171")
        self.log.delete("1.0", "end")
        for r in self.ctx.db.recent_logs():
            self.log.insert("end", f"[{r['ts']}] {r['actor']:<12} {r['action']:<18} {r['detail'] or ''}\n")
