import time
from tkinter import messagebox

import cv2
import customtkinter as ctk
from PIL import Image

from auth.biometric import FaceEngine
from auth.dongle import scan_dongles
from auth.engine import AuthError


class LoginView(ctk.CTkFrame):
    def __init__(self, master, ctx, on_success):
        super().__init__(master)
        self.ctx, self.on_success = ctx, on_success
        self.face = FaceEngine()
        self.cap, self.buffer, self.dongles = None, [], []
        self.last_face, self.running = 0.0, False

        ctk.CTkLabel(self, text="EvidenceLock", font=ctk.CTkFont(size=30, weight="bold")).pack(pady=(22, 0))
        ctk.CTkLabel(self, text="Repository Bukti Digital Persidangan", text_color="gray").pack()
        self.mode_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.mode_lbl.pack(pady=6)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(pady=6)
        left = ctk.CTkFrame(body)
        left.grid(row=0, column=0, padx=14, sticky="ns")
        bold = ctk.CTkFont(size=14, weight="bold")

        ctk.CTkLabel(left, text="1. USB Dongle", font=bold).pack(anchor="w", padx=18, pady=(18, 2))
        self.dongle_lbl = ctk.CTkLabel(left, text="Memindai...", justify="left", wraplength=280)
        self.dongle_lbl.pack(anchor="w", padx=18)
        ctk.CTkLabel(left, text="2. Password", font=bold).pack(anchor="w", padx=18, pady=(18, 2))
        self.pw = ctk.CTkEntry(left, show="*", width=280)
        self.pw.pack(padx=18)
        self.pw.bind("<Return>", lambda _e: self._submit())
        self.btn = ctk.CTkButton(left, text="Login", command=self._submit, height=38)
        self.btn.pack(padx=18, pady=(22, 8), fill="x")
        self.status = ctk.CTkLabel(left, text="", wraplength=280, justify="left")
        self.status.pack(padx=18, pady=(0, 18))

        right = ctk.CTkFrame(body)
        right.grid(row=0, column=1, padx=14)
        ctk.CTkLabel(right, text="3. Biometrik Wajah", font=bold).pack(anchor="w", padx=18, pady=(18, 6))
        self.video = ctk.CTkLabel(right, text="Membuka kamera...", width=480, height=360)
        self.video.pack(padx=18, pady=(0, 8))
        self.face_lbl = ctk.CTkLabel(right, text="Wajah: belum terdeteksi", text_color="gray")
        self.face_lbl.pack(pady=(0, 14))

    def start(self):
        enrolled = self.ctx.auth.is_enrolled()
        self.mode_lbl.configure(
            text="Mode Login" if enrolled else "Pendaftaran Awal: dongle, wajah, dan password akan didaftarkan",
            text_color="#4ade80" if enrolled else "#fbbf24")
        self.btn.configure(text="Login" if enrolled else "Daftarkan & Masuk")
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self._poll_dongle()
        self._tick()

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def _poll_dongle(self):
        if not self.running:
            return
        self.dongles = scan_dongles()
        if self.dongles:
            d = self.dongles[0]
            self.dongle_lbl.configure(text=f"TERDETEKSI  {d.mountpoint}\nSerial: {d.serial}", text_color="#4ade80")
        else:
            self.dongle_lbl.configure(text="Colokkan USB flashdisk dongle", text_color="#f87171")
        self.after(2000, self._poll_dongle)

    def _tick(self):
        if not self.running:
            return
        ok, frame = self.cap.read() if self.cap is not None else (False, None)
        if ok:
            frame = cv2.flip(frame, 1)
            box = self.face.detect(frame)
            if box is not None:
                self.buffer = (self.buffer + [self.face.encode(frame, box)])[-10:]
                self.last_face = time.time()
                x, y, w, h = box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 0), 2)
                self.face_lbl.configure(text="Wajah: terdeteksi", text_color="#4ade80")
            else:
                self.face_lbl.configure(text="Wajah: belum terdeteksi", text_color="gray")
            img = ctk.CTkImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), size=(480, 360))
            self.video.configure(image=img, text="")
            self.video.image = img
        else:
            self.video.configure(text="Kamera tidak tersedia")
        self.after(40, self._tick)

    def _fail(self, msg):
        self.status.configure(text=msg, text_color="#f87171")

    def _submit(self):
        if not self.dongles:
            return self._fail("USB dongle belum terdeteksi")
        if len(self.buffer) < 5 or time.time() - self.last_face > 1.0:
            return self._fail("Wajah belum terdeteksi stabil. Hadap kamera")
        vec = FaceEngine.average(self.buffer[-5:])
        try:
            if self.ctx.auth.is_enrolled():
                keyring, _ = self.ctx.auth.verify(self.pw.get(), self.dongles, vec)
            else:
                keyring = self.ctx.auth.enroll(self.pw.get(), self.dongles[0], vec)
        except AuthError as e:
            self.ctx.db.log("unknown", "LOGIN_FAILED", str(e))
            return self._fail(str(e))
        self.ctx.keyring = keyring
        self.on_success()
