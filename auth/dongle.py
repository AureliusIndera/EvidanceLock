import ctypes
import os
import platform
import plistlib
import subprocess
from dataclasses import dataclass

import psutil


@dataclass
class Dongle:
    device: str
    mountpoint: str
    serial: str
    label: str


def _is_removable(part) -> bool:
    system = platform.system()
    if system == "Windows":
        return "removable" in part.opts.lower()
    if system == "Darwin":
        return part.mountpoint.startswith("/Volumes/")
    return part.mountpoint.startswith(("/media", "/run/media", "/mnt"))


def _volume_serial(part) -> str | None:
    system = platform.system()
    if system == "Windows":
        serial = ctypes.c_uint32(0)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(part.mountpoint), None, 0, ctypes.byref(serial), None, None, None, 0)
        return f"{serial.value:08X}" if ok else None
    if system == "Linux":
        base = "/dev/disk/by-uuid"
        if os.path.isdir(base):
            target = os.path.realpath(part.device)
            for name in os.listdir(base):
                if os.path.realpath(os.path.join(base, name)) == target:
                    return name
        return None
    if system == "Darwin":
        out = subprocess.run(["diskutil", "info", "-plist", part.device], capture_output=True)
        return plistlib.loads(out.stdout).get("VolumeUUID") if out.returncode == 0 else None
    return None


def scan_dongles() -> list[Dongle]:
    found = []
    for part in psutil.disk_partitions(all=False):
        if not _is_removable(part):
            continue
        serial = _volume_serial(part)
        if serial:
            found.append(Dongle(part.device, part.mountpoint, serial, part.mountpoint))
    return found
