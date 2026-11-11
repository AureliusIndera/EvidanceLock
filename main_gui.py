from tkinter import messagebox

import customtkinter as ctk

from auth.dongle import scan_dongles
from ui.blockchain_view import BlockchainView
from ui.context import AppContext
from ui.dashboard_view import DashboardView
from ui.input_view import InputView
from ui.login_view import LoginView
from ui.viewer_view import ViewerView

DONGLE_CHECK_MS = 2000


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.blocked = False
        self.main = None
        self.login = None
        self._watch_id = None
        self.title("EvidenceLock - Repository Bukti Digital Persidangan")
        self.geometry("1180x780")
        self.minsize(1000, 700)
        self.ctx = AppContext()
        if self.ctx.auth.is_enrolled() and self.ctx.auth.find_registered(scan_dongles()) is None:
            self.blocked = True
            self.withdraw()
            self.ctx.db.log("system", "STARTUP_DENIED", "Dongle terdaftar tidak ditemukan")
            messagebox.showerror("EvidenceLock", "USB dongle terdaftar tidak ditemukan.\n"
                                 "Colokkan dongle, lalu jalankan ulang aplikasi.")
            self.destroy()
            return
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._show_login()

    def _show_login(self):
        self.login = LoginView(self, self.ctx, self._on_login)
        self.login.pack(fill="both", expand=True)
        self.login.start()

    def _on_login(self):
        self.login.stop()
        self.login.destroy()
        self.login = None
        self.ctx.record("SESSION_START", "Autentikasi 3 faktor berhasil")
        self._build_main()
        self._watch_id = self.after(DONGLE_CHECK_MS, self._watch_dongle)

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=12, pady=10)
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="EvidenceLock", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Logout", width=90, fg_color="#475569",
                      command=lambda: self._end_session("SESSION_END", "Logout")).pack(side="right")
        self.tabs = ctk.CTkTabview(self.main, command=self._on_tab)
        self.tabs.pack(fill="both", expand=True)
        self.views = {
            "Dashboard": DashboardView(self.tabs.add("Dashboard"), self.ctx),
            "Input & Pengolahan Bukti": InputView(self.tabs.add("Input & Pengolahan Bukti"), self.ctx),
            "Viewer Bukti": ViewerView(self.tabs.add("Viewer Bukti"), self.ctx),
            "Inspector Blockchain": BlockchainView(self.tabs.add("Inspector Blockchain"), self.ctx),
        }
        for v in self.views.values():
            v.pack(fill="both", expand=True)
        self._on_tab()

    def _on_tab(self):
        self.views[self.tabs.get()].refresh()

    def _watch_dongle(self):
        self._watch_id = None
        if self.main is None:
            return
        if self.ctx.auth.find_registered(scan_dongles()) is None:
            self._end_session("SESSION_LOCKED", "Dongle dicabut, sesi dikunci")
            messagebox.showwarning("EvidenceLock", "USB dongle dicabut. Sesi dikunci.\n"
                                   "Colokkan kembali dongle dan login ulang.")
            return
        self._watch_id = self.after(DONGLE_CHECK_MS, self._watch_dongle)

    def _end_session(self, action, detail):
        if self._watch_id is not None:
            self.after_cancel(self._watch_id)
            self._watch_id = None
        self.ctx.record(action, detail)
        self.ctx.keyring = None
        if self.main is not None:
            self.main.destroy()
            self.main = None
        self._show_login()

    def _close(self):
        if self._watch_id is not None:
            self.after_cancel(self._watch_id)
        if self.login is not None and self.login.winfo_exists():
            self.login.stop()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    if not app.blocked:
        app.mainloop()