"""HyperTweak - Android device settings tweaker via ADB."""

from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.widgets.scrolled import ScrolledFrame

try:
    from ppadb.client import Client as AdbClient
except Exception:
    AdbClient = None  # type: ignore[misc,assignment]

import adb
from config import ApplySelection, SettingsPayload, build_shell_commands
from ui import (
    build_advanced_settings,
    build_command_console,
    build_current_device_settings,
    build_quick_toggles,
)
from ui.shared import apply_current_kv


class HyperTweakApp:
    def __init__(self) -> None:
        self.root = tb.Window(themename="darkly")
        self.root.title("HyperTweak")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        self._ui_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._adb_client: Any | None = None
        self._device: Any | None = None
        self._device_name: str | None = None

        self._build_ui()
        self._start_queue_poller()
        self._run_bg("start ADB server", self._ensure_adb_server_running_bg)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=5)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(14, 12, 14, 10))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(1, weight=1)

        self.btn_connect = ttk.Button(
            header,
            text="Connect Device",
            command=self.connect_device,
            width=18,
            style="primary.TButton",
        )
        self.btn_connect.grid(row=0, column=0, sticky="w")

        self.lbl_device = ttk.Label(header, text="No device connected", anchor="w")
        self.lbl_device.grid(row=0, column=1, sticky="ew", padx=(12, 8))

        self.lbl_adb_hint = ttk.Label(
            header,
            text="ADB server: 127.0.0.1:5037",
            anchor="e",
            foreground="#9aa4b2",
        )
        self.lbl_adb_hint.grid(row=0, column=2, sticky="e")

        self.scroller = ScrolledFrame(self.root, autohide=False, padding=(14, 8, 26, 10))
        self.scroller.grid(row=1, column=0, sticky="nsew")

        page = self.scroller
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        self._init_vars()
        self._vcmd_int = (self.root.register(self._validate_int_entry), "%P")

        content = ttk.Frame(page)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)

        r = 0
        r = build_current_device_settings(content, self, r)
        r = build_quick_toggles(content, self, r)
        r = build_advanced_settings(content, self, r)

        footer = ttk.Frame(self.root, padding=(14, 6, 14, 8))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.columnconfigure(0, weight=1)

        btns = ttk.Frame(footer)
        btns.grid(row=0, column=0, sticky="e")

        self.btn_apply = ttk.Button(
            btns,
            text="Apply Settings",
            command=self.apply_settings,
            style="success.TButton",
            width=18,
        )
        self.btn_apply.grid(row=0, column=0, sticky="e")

        self.btn_reboot = ttk.Button(
            btns,
            text="Reboot",
            command=self.reboot_device,
            style="danger.TButton",
            width=10,
        )
        self.btn_reboot.grid(row=0, column=1, sticky="e", padx=(10, 0))

        right_wrap = ttk.Frame(self.root, padding=(10, 8, 14, 10), width=360)
        right_wrap.grid(row=1, column=1, sticky="nsew")
        self.root.rowconfigure(1, weight=1)
        right_wrap.rowconfigure(0, weight=1)
        right_wrap.grid_propagate(False)

        notebook = ttk.Notebook(right_wrap)
        notebook.grid(row=0, column=0, sticky="nsew")
        right_wrap.columnconfigure(0, weight=1)

        log_tab = ttk.Frame(notebook)
        notebook.add(log_tab, text="Status Log")
        log_tab.rowconfigure(1, weight=1)
        log_tab.columnconfigure(0, weight=1)

        log_header = ttk.Frame(log_tab)
        log_header.grid(row=0, column=0, sticky="ew")
        log_header.columnconfigure(0, weight=1)

        ttk.Label(log_header, text="Status Log").grid(row=0, column=0, sticky="w")
        self.btn_clear = ttk.Button(log_header, text="Clear", command=self._clear_log, width=10)
        self.btn_clear.grid(row=0, column=1, sticky="e")

        self.txt_log = tk.Text(
            log_tab,
            height=1,
            wrap="word",
            padx=10,
            pady=6,
            bg="#0e1116",
            fg="#e7eaf0",
            insertbackground="#e7eaf0",
            relief="flat",
        )
        self.txt_log.grid(row=1, column=0, sticky="nsew")

        console_tab = build_command_console(notebook, self)
        notebook.add(console_tab, text="Command Console")

        self._log("Ready. Connect a device via USB debugging.")
        self._append_console("Console ready.\n")

    def _init_vars(self) -> None:
        self.var_v = tk.IntVar(value=1)
        self.var_c = tk.IntVar(value=1)
        self.var_g = tk.IntVar(value=1)
        self.var_cpulevel = tk.IntVar(value=3)
        self.var_gpulevel = tk.IntVar(value=3)
        self.var_advanced_visual_release = tk.IntVar(value=1)
        self.var_temp_enable = tk.BooleanVar(value=False)
        self.var_temp_bottom = tk.StringVar(value="35")
        self.var_temp_ceiling = tk.StringVar(value="45")
        self.var_home_anim = tk.StringVar(value="Balanced")
        self.var_recents_style = tk.StringVar(value="Vertically")
        self.var_background_blur_supported = tk.StringVar(value="Disabled")

        self.apply_device_level_list = tk.BooleanVar(value=True)
        self.apply_computility = tk.BooleanVar(value=True)
        self.apply_advanced_visual_release = tk.BooleanVar(value=True)
        self.apply_temp_limit = tk.BooleanVar(value=False)
        self.apply_miui_home_animation = tk.BooleanVar(value=True)
        self.apply_recents_style = tk.BooleanVar(value=True)
        self.apply_background_blur_supported = tk.BooleanVar(value=True)

        self.cur_device_level_list = tk.StringVar(value="—")
        self.cur_cpulevel = tk.StringVar(value="—")
        self.cur_gpulevel = tk.StringVar(value="—")
        self.cur_advanced_visual_release = tk.StringVar(value="—")
        self.cur_window_animation_scale = tk.StringVar(value="—")
        self.cur_transition_animation_scale = tk.StringVar(value="—")
        self.cur_animator_duration_scale = tk.StringVar(value="—")
        self.cur_temp_limit_enabled = tk.StringVar(value="—")
        self.cur_temp_limit_bottom = tk.StringVar(value="—")
        self.cur_temp_limit_ceiling = tk.StringVar(value="—")
        self.cur_miui_home_animation_rate = tk.StringVar(value="—")
        self.cur_recents_style = tk.StringVar(value="—")
        self.cur_background_blur_supported = tk.StringVar(value="—")

    def _sync_temp_enabled_state(self) -> None:
        if not bool(self.apply_temp_limit.get()):
            try:
                self.ent_temp_bottom.configure(state="disabled")
                self.ent_temp_ceiling.configure(state="disabled")
            except (AttributeError, tk.TclError):
                pass
            return
        state = "normal" if self.var_temp_enable.get() else "disabled"
        self.ent_temp_bottom.configure(state=state)
        self.ent_temp_ceiling.configure(state=state)

    # -------------------------
    # ADB
    # -------------------------
    def connect_device(self) -> None:
        self._run_bg("connect", self._connect_device_bg)

    def _connect_device_bg(self) -> None:
        if AdbClient is None:
            raise RuntimeError("pure-python-adb not installed. Run: pip install -r requirements.txt")

        self._log_async("Connecting to ADB server 127.0.0.1:5037 ...")
        client = AdbClient(host="127.0.0.1", port=5037)
        try:
            devices = client.devices()
        except OSError as e:
            if getattr(e, "winerror", None) == 10061:
                self._log_async("ADB server not running. Attempting to start it...")
                self._ensure_adb_server_running_bg()
                devices = client.devices()
            else:
                raise

        if not devices:
            raise RuntimeError("No devices found. Ensure USB debugging is enabled and run `adb devices`.")

        device = devices[0]
        serial = getattr(device, "serial", "<unknown>")
        try:
            out = device.shell("getprop ro.product.model").strip()
        except Exception:
            out = ""

        self._adb_client = client
        self._device = device
        name = f"{serial}" + (f" ({out})" if out else "")
        self._device_name = name
        self._ui_queue.put(("device", name))
        self._log_async(f"Connected to: {name}")
        self._ui_queue.put(("auto_refresh", "1"))

    def _ensure_adb_server_running_bg(self) -> None:
        self._log_async("Initializing ADB server (adb start-server)...")
        adb.start_adb_server()
        self._log_async("ADB server is running.", level="success")

    def reboot_device(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        self._run_bg("reboot", self._reboot_device_bg)

    def _reboot_device_bg(self) -> None:
        assert self._device is not None
        self._log_async("Rebooting device...")
        self._device.shell("reboot")
        self._log_async("Reboot command sent.", level="success")

    def refresh_current_settings(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        self._run_bg("refresh", self._refresh_current_settings_bg)

    def _current_snapshot(self) -> dict[str, str]:
        return {
            "window_animation_scale": self.cur_window_animation_scale.get(),
            "transition_animation_scale": self.cur_transition_animation_scale.get(),
            "animator_duration_scale": self.cur_animator_duration_scale.get(),
            "task_stack_view_layout_style": self.cur_recents_style.get(),
            "deviceLevelList": self.cur_device_level_list.get(),
            "cpulevel": self.cur_cpulevel.get(),
            "gpulevel": self.cur_gpulevel.get(),
            "advanced_visual_release": self.cur_advanced_visual_release.get(),
            "rt_enable_templimit": self.cur_temp_limit_enabled.get(),
            "rt_templimit_bottom": self.cur_temp_limit_bottom.get(),
            "rt_templimit_ceiling": self.cur_temp_limit_ceiling.get(),
            "miui_home_animation_rate": self.cur_miui_home_animation_rate.get(),
            "background_blur_supported": self.cur_background_blur_supported.get(),
        }

    def save_current_settings(self) -> None:
        snapshot = self._current_snapshot()
        default_name = "hypertweak_settings.json"
        if self._device_name:
            safe = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", self._device_name).strip()
            safe = re.sub(r"\s+", " ", safe)
            if safe:
                default_name = f"{safe}.json"

        path = filedialog.asksaveasfilename(
            title="Save current settings",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=default_name,
        )
        if not path:
            return

        data = {
            "schema": 1,
            "saved_at_unix": int(time.time()),
            "values": snapshot,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._log(f"Saved current values to: {path}", level="success")

    def load_current_settings(self) -> None:
        path = filedialog.askopenfilename(
            title="Load settings file",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            values = data.get("values", data)
            if not isinstance(values, dict):
                raise ValueError("Invalid file format: expected JSON object.")

            recents_style_reverse = {"0": "Vertically", "1": "Horizontally", "2": "Stacked"}
            applied = 0
            for k, v in values.items():
                if v is None:
                    continue
                key = str(k)
                val = str(v).strip()

                if key == "deviceLevelList":
                    m = re.search(r"v:(\d+)\s*,\s*c:(\d+)\s*[.,]\s*g:(\d+)", val)
                    if m:
                        self.var_v.set(int(m.group(1)))
                        self.var_c.set(int(m.group(2)))
                        self.var_g.set(int(m.group(3)))
                        applied += 1
                elif key == "cpulevel" and val.isdigit():
                    self.var_cpulevel.set(int(val))
                    applied += 1
                elif key == "gpulevel" and val.isdigit():
                    self.var_gpulevel.set(int(val))
                    applied += 1
                elif key == "advanced_visual_release" and val.isdigit():
                    self.var_advanced_visual_release.set(int(val))
                    applied += 1
                elif key == "rt_enable_templimit":
                    self.var_temp_enable.set(val in ("1", "true", "True", "enabled", "on", "ON"))
                    self._sync_temp_enabled_state()
                    applied += 1
                elif key == "rt_templimit_bottom" and val.isdigit():
                    self.var_temp_bottom.set(val)
                    applied += 1
                elif key == "rt_templimit_ceiling" and val.isdigit():
                    self.var_temp_ceiling.set(val)
                    applied += 1
                elif key == "miui_home_animation_rate":
                    home_anim_reverse = {"0": "Relaxed", "1": "Balanced", "2": "Fast"}
                    if val in home_anim_reverse:
                        self.var_home_anim.set(home_anim_reverse[val])
                        applied += 1
                    elif val in ("Relaxed", "Balanced", "Fast"):
                        self.var_home_anim.set(val)
                        applied += 1
                elif key == "task_stack_view_layout_style":
                    if val in recents_style_reverse:
                        self.var_recents_style.set(recents_style_reverse[val])
                        applied += 1
                    elif val in ("Vertically", "Horizontally", "Stacked"):
                        self.var_recents_style.set(val)
                        applied += 1
                elif key == "background_blur_supported":
                    vlow = val.lower()
                    if vlow in ("1", "true", "enabled"):
                        self.var_background_blur_supported.set("Enabled")
                        applied += 1
                    elif vlow in ("0", "false", "disabled"):
                        self.var_background_blur_supported.set("Disabled")
                        applied += 1

            self._log(f"Loaded {applied} value(s) from: {path}", level="success")
        except Exception as e:
            self._log(f"Load failed: {e}", level="error")

    def _refresh_current_settings_bg(self) -> None:
        assert self._device is not None
        queries: list[tuple[str, str]] = [
            ("window_animation_scale", "settings get global window_animation_scale"),
            ("transition_animation_scale", "settings get global transition_animation_scale"),
            ("animator_duration_scale", "settings get global animator_duration_scale"),
            ("task_stack_view_layout_style", "settings get global task_stack_view_layout_style"),
            ("deviceLevelList", "settings get system deviceLevelList"),
            ("cpulevel", "getprop persist.sys.computility.cpulevel"),
            ("gpulevel", "getprop persist.sys.computility.gpulevel"),
            ("advanced_visual_release", "getprop persist.sys.advanced_visual_release"),
            ("rt_enable_templimit", "settings get system rt_enable_templimit"),
            ("rt_templimit_bottom", "settings get system rt_templimit_bottom"),
            ("rt_templimit_ceiling", "settings get system rt_templimit_ceiling"),
            ("miui_home_animation_rate", "settings get system miui_home_animation_rate"),
            ("background_blur_supported", "getprop persist.sys.background_blur_supported"),
        ]
        self._log_async("Refreshing current settings from device...")
        for key, cmd in queries:
            val = self._device.shell(cmd).strip()
            if not val:
                val = "—"
            self._ui_queue.put(("current", f"{key}={val}"))
        self._log_async("Refresh complete.", level="success")

    # -------------------------
    # Apply Settings
    # -------------------------
    def apply_settings(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        payload = self._gather_payload()
        selection = ApplySelection(
            device_level_list=bool(self.apply_device_level_list.get()),
            computility=bool(self.apply_computility.get()),
            advanced_visual_release=bool(self.apply_advanced_visual_release.get()),
            temp_limit=bool(self.apply_temp_limit.get()),
            miui_home_animation=bool(self.apply_miui_home_animation.get()),
            recents_style=bool(self.apply_recents_style.get()),
            background_blur_supported=bool(self.apply_background_blur_supported.get()),
        )
        self._run_bg("apply", lambda: self._apply_settings_bg(payload, selection))

    def _gather_payload(self) -> SettingsPayload:
        bottom = int(self.var_temp_bottom.get() or "0")
        ceiling = int(self.var_temp_ceiling.get() or "0")
        return SettingsPayload(
            v=int(self.var_v.get()),
            c=int(self.var_c.get()),
            g=int(self.var_g.get()),
            cpulevel=int(self.var_cpulevel.get()),
            gpulevel=int(self.var_gpulevel.get()),
            advanced_visual_release=int(self.var_advanced_visual_release.get()),
            temp_limit_enabled=bool(self.var_temp_enable.get()),
            temp_limit_bottom=bottom,
            temp_limit_ceiling=ceiling,
            miui_home_animation=str(self.var_home_anim.get()),
            recents_style=str(self.var_recents_style.get()),
            background_blur_supported=str(self.var_background_blur_supported.get()),
        )

    def _apply_settings_bg(self, payload: SettingsPayload, selection: ApplySelection) -> None:
        assert self._device is not None
        cmds = build_shell_commands(payload, selection)
        if not cmds:
            self._log_async("No sections selected; nothing to apply.", level="error")
            return
        self._log_async(f"Applying {len(cmds)} command(s)...")
        started = time.time()
        for i, cmd in enumerate(cmds, start=1):
            self._log_async(f"[{i}/{len(cmds)}] {cmd}")
            self._device.shell(cmd)
        elapsed_ms = int((time.time() - started) * 1000)
        self._log_async(f"Done in {elapsed_ms} ms.", level="success")

    # -------------------------
    # Command Console
    # -------------------------
    def run_custom_command(self) -> None:
        cmd = self.txt_custom_cmd.get("1.0", "end-1c").strip()
        if not cmd:
            return
        self._ui_queue.put(("console_clear", ""))
        if self._device is None:
            self._append_console("[!] No device connected. Click 'Connect Device' first.\n")
            return
        self._run_bg("custom_cmd", lambda: self._run_custom_command_bg(cmd))

    def _append_console(self, text: str) -> None:
        self._ui_queue.put(("console", text))

    def _append_console_ui(self, text: str) -> None:
        self.txt_console.configure(state="normal")
        self.txt_console.insert("end", text)
        self.txt_console.see("end")
        self.txt_console.configure(state="disabled")

    def _run_custom_command_bg(self, cmd: str) -> None:
        assert self._device is not None
        commands = self._split_shell_commands(cmd)
        if not commands:
            return
        self._append_console(f"Running {len(commands)} command(s)...\n\n")
        for one in commands:
            self._append_console(f"$ {one}\n")
            try:
                out = self._device.shell(one)
            except Exception as e:
                self._append_console(f"ERROR: {e}\n\n")
                continue
            out = (out or "").rstrip()
            self._append_console(f"{out}\n\n" if out else "\n")

    def _split_shell_commands(self, text: str) -> list[str]:
        s = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not s:
            return []
        parts: list[str] = []
        buf: list[str] = []
        quote: str | None = None
        for ch in s:
            if quote is not None:
                buf.append(ch)
                if ch == quote:
                    quote = None
                continue
            if ch in ("'", '"'):
                quote = ch
                buf.append(ch)
                continue
            if ch == ";":
                part = "".join(buf).strip()
                if part:
                    parts.append(part)
                buf = []
                continue
            if ch == "\n":
                buf.append(" ")
                continue
            buf.append(ch)
        tail = "".join(buf).strip()
        if tail:
            parts.append(tail)
        return parts

    # -------------------------
    # Quick Toggles
    # -------------------------
    def toggle_animations(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        disable = not getattr(self, "_animations_disabled", False)
        self._run_bg("animations", lambda: self._toggle_animations_bg(disable))

    def _toggle_animations_bg(self, disable: bool) -> None:
        assert self._device is not None
        value = "0" if disable else "1"
        cmds = [
            f"settings put global window_animation_scale {value}",
            f"settings put global transition_animation_scale {value}",
            f"settings put global animator_duration_scale {value}",
        ]
        self._append_console(f"Running {len(cmds)} command(s)...\n\n")
        errors: list[str] = []

        def run_one(c: str) -> None:
            try:
                self._device.shell(c)
            except Exception as e:
                errors.append(f"{c} -> {e}")

        threads: list[threading.Thread] = []
        for c in cmds:
            self._append_console(f"$ {c}\n")
            t = threading.Thread(target=run_one, args=(c,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        self._animations_disabled = disable
        self._ui_queue.put(("anim_btn_text", "Enable animations" if disable else "Disable animations"))

        if errors:
            self._append_console("\nERRORS:\n" + "\n".join(errors) + "\n")
            self._log_async("Animation toggle completed with errors.", level="error")
        else:
            self._append_console("\nDone.\n")
            self._log_async("Animation toggle applied.", level="success")

    def set_recents_style(self, style: str) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        style_map = {"Vertically": 0, "Horizontally": 1, "Stacked": 2}
        if style not in style_map:
            self._log(f"Unknown recents style: {style}", level="error")
            return
        self.var_recents_style.set(style)
        cmd = f"settings put global task_stack_view_layout_style {style_map[style]}"
        self._run_bg("recents_style", lambda: self._run_one_quick_cmd_bg(style, cmd))

    def _run_one_quick_cmd_bg(self, label: str, cmd: str) -> None:
        assert self._device is not None
        self._append_console(f"$ {cmd}\n")
        try:
            out = self._device.shell(cmd)
        except Exception as e:
            self._append_console(f"ERROR: {e}\n")
            self._log_async(f"Recents style '{label}' failed.", level="error")
            return
        out = (out or "").rstrip()
        if out:
            self._append_console(f"{out}\n")
        self._log_async(f"Recents style set: {label}", level="success")

    # -------------------------
    # Background + polling
    # -------------------------
    def _run_bg(self, name: str, fn: Callable[[], None]) -> None:
        def runner() -> None:
            try:
                self._ui_queue.put(("busy", "1"))
                fn()
            except Exception as e:
                self._log_async(f"{name} failed: {e}", level="error")
            finally:
                self._ui_queue.put(("busy", "0"))

        threading.Thread(target=runner, daemon=True).start()

    def _start_queue_poller(self) -> None:
        def poll() -> None:
            try:
                while True:
                    kind, msg = self._ui_queue.get_nowait()
                    if kind == "log":
                        self._log(msg)
                    elif kind == "log_success":
                        self._log(msg, level="success")
                    elif kind == "log_error":
                        self._log(msg, level="error")
                    elif kind == "device":
                        self.lbl_device.configure(text=f"Connected: {msg}")
                    elif kind == "auto_refresh":
                        self.refresh_current_settings()
                    elif kind == "current":
                        apply_current_kv(self, msg)
                    elif kind == "busy":
                        busy = msg == "1"
                        self.btn_connect.configure(state=("disabled" if busy else "normal"))
                        self.btn_reboot.configure(state=("disabled" if busy else "normal"))
                        self.btn_apply.configure(state=("disabled" if busy else "normal"))
                        for btn in (
                            getattr(self, "btn_run_custom_cmd", None),
                            getattr(self, "btn_toggle_animations", None),
                            getattr(self, "btn_recents_vertical", None),
                            getattr(self, "btn_recents_horizontal", None),
                            getattr(self, "btn_recents_stacked", None),
                        ):
                            if btn is not None:
                                try:
                                    btn.configure(state=("disabled" if busy else "normal"))
                                except Exception:
                                    pass
                    elif kind == "console":
                        self._append_console_ui(msg)
                    elif kind == "console_clear":
                        self.txt_console.configure(state="normal")
                        self.txt_console.delete("1.0", "end")
                        self.txt_console.configure(state="disabled")
                    elif kind == "anim_btn_text":
                        try:
                            self.btn_toggle_animations.configure(text=msg)
                        except Exception:
                            pass
            except queue.Empty:
                pass
            self.root.after(120, poll)

        self.root.after(120, poll)

    def _log_async(self, message: str, level: str = "info") -> None:
        kind = "log"
        if level == "success":
            kind = "log_success"
        elif level == "error":
            kind = "log_error"
        self._ui_queue.put((kind, message))

    def _log(self, message: str, level: str = "info") -> None:
        prefix = {"info": "[*] ", "success": "[+] ", "error": "[!] "}.get(level, "[*] ")
        line = f"{prefix}{message}\n"
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", line)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    def _validate_int_entry(self, proposed: str) -> bool:
        return proposed == "" or proposed.isdigit()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    HyperTweakApp().run()
