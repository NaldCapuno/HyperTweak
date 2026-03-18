"""ADB path resolution and server startup for HyperTweak."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def get_adb_path() -> str:
    """
    Resolve path to adb.exe.
    Prefers platform-tools next to executable, then next to script, then PATH.
    """
    adb: str | None = None

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidate = os.path.join(exe_dir, "platform-tools", "adb.exe")
        if os.path.exists(candidate):
            adb = candidate

    if not adb:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(script_dir, "platform-tools", "adb.exe")
        if os.path.exists(candidate):
            adb = candidate

    if not adb:
        adb = shutil.which("adb")

    if not adb:
        raise RuntimeError(
            "ADB not found. Put platform-tools next to the app (platform-tools/adb.exe) "
            "or install Android platform-tools and ensure `adb` is in PATH."
        )

    return adb


def start_adb_server(adb_path: str | None = None) -> None:
    """
    Start ADB server. If already running, adb prints a benign message.
    Raises RuntimeError on failure.
    """
    adb = adb_path or get_adb_path()
    proc = subprocess.run(
        [adb, "start-server"],
        capture_output=True,
        text=True,
        timeout=15,
        shell=False,
    )
    if proc.returncode != 0:
        out = (proc.stdout or "") + (proc.stderr or "")
        out = out.strip() or "unknown error"
        raise RuntimeError(f"Failed to start ADB server: {out}")
