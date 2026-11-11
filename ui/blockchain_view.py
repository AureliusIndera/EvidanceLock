import json
from datetime import datetime

import customtkinter as ctk


class BlockchainView(ctk.CTkFrame):
    def __init__(self, master, ctx):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.issues = None
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=4)
        ctk.CTkButton(bar, text="Validasi Rantai", command=self._validate).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Simulasi Tampering (memori)", command=self._tamper, fg_color="#b45309").pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Muat Ulang dari DB", command=self._reload, fg_color="#475569").pack(side="left", padx=4)
        self.status = ctk.CTkLabel(bar, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.status.pack(side="left", padx=14)
        self.list = ctk.CTkScrollableFrame(self)
        self.list.pack(fill="both", expand=True)

    def refresh(self):
        self.issues = None
        self.status.configure(text="")
        self.render()

    def render(self):
        for w in self.list.winfo_children():
            w.destroy()
        for b in self.ctx.chain.chain:
            if self.issues is None:
                color = ("#e2e8f0", "#1e293b")
            elif b.index in self.issues:
                color = "#7f1d1d"
            else:
                color = "#14532d"
            card = ctk.CTkFrame(self.list, fg_color=color)
            card.pack(fill="x", padx=8, pady=(4, 0))
            ts = "genesis" if b.timestamp == 0 else datetime.fromtimestamp(b.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            text = (f"BLOK #{b.index}   {ts}   nonce={b.nonce}\n"
                    f"Data     : {json.dumps(b.data, ensure_ascii=False)}\n"
                    f"Data hash: {b.data_hash}\nPrev hash: {b.previous_hash}\nHash     : {b.hash}")
            if self.issues and b.index in self.issues:
                text += "\nMASALAH  : " + "; ".join(self.issues[b.index])
            ctk.CTkLabel(card, text=text, justify="left", anchor="w", wraplength=980,
                         font=ctk.CTkFont(family="Courier", size=11)).pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(self.list, text="v", text_color="gray").pack()

    def _validate(self):
        ok, self.issues = self.ctx.chain.validate()
        self.status.configure(text="RANTAI VALID" if ok else f"RANTAI RUSAK ({len(self.issues)} blok bermasalah)",
                              text_color="#4ade80" if ok else "#f87171")
        self.render()

    def _tamper(self):
        if len(self.ctx.chain.chain) < 2:
            return self.status.configure(text="Belum ada blok bukti untuk disimulasikan", text_color="#fbbf24")
        self.ctx.chain.chain[1].data["detail"] = "DATA DIMANIPULASI"
        self._validate()

    def _reload(self):
        self.ctx.reload_chain()
        self.refresh()
