from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, ttk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.scrolled import ScrolledFrame
try:
    from ppadb.client import Client as AdbClient  # pure-python-adb
except Exception:  # pragma: no cover
    AdbClient = None  # type: ignore[misc,assignment]


@dataclass(frozen=True)
class SettingsPayload:
    v: int
    c: int
    g: int
    cpulevel: int
    gpulevel: int
    advanced_visual_release: int
    temp_limit_enabled: bool
    temp_limit_bottom: int
    temp_limit_ceiling: int
    miui_home_animation: str
    recents_style: str
    background_blur_supported: str


@dataclass(frozen=True)
class ApplySelection:
    device_level_list: bool
    computility: bool
    advanced_visual_release: bool
    temp_limit: bool
    miui_home_animation: bool
    recents_style: bool
    background_blur_supported: bool


def build_shell_commands(payload: SettingsPayload, selection: ApplySelection) -> list[str]:
    """
    Placeholder mapping.

    Replace the keys/values here to match your ROM/device expectation.
    Default behavior uses:
      settings put system <key> <value>
    """
    def put(key: str, value: Any) -> str:
        return f"settings put system {key} {value}"

    def put_global(key: str, value: Any) -> str:
        return f"settings put global {key} {value}"

    def mqsas_setprop(prop_and_value: str) -> str:
        # Matches: service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "<prop> <value>" s16 "/storage/emulated/0/log.txt" i32 600
        return (
            'service call miui.mqsas.IMQSNative 21 '
            'i32 1 s16 "setprop" i32 1 '
            f's16 "{prop_and_value}" '
            's16 "/storage/emulated/0/log.txt" i32 600'
        )

    # Device Level List is a single value containing v/c/g together.
    # Format requested: v:n,c:n.g:n
    device_level_list = f"v:{payload.v},c:{payload.c},g:{payload.g}"

    recents_style_map = {
        "Vertically": 0,
        "Horizontally": 1,
        "Stacked": 2,
    }
    recents_style_value = recents_style_map.get(str(payload.recents_style), payload.recents_style)

    home_anim_map = {
        "Relaxed": 0,
        "Balanced": 1,
        "Fast": 2,
    }
    home_anim_value = home_anim_map.get(str(payload.miui_home_animation), payload.miui_home_animation)

    cmds: list[str] = []

    if selection.device_level_list:
        cmds.append(put("deviceLevelList", device_level_list))

    if selection.computility:
        cmds.append(mqsas_setprop(f"persist.sys.computility.cpulevel {payload.cpulevel}"))
        cmds.append(mqsas_setprop(f"persist.sys.computility.gpulevel {payload.gpulevel}"))

    if selection.advanced_visual_release:
        cmds.append(mqsas_setprop(f"persist.sys.advanced_visual_release {payload.advanced_visual_release}"))

    if selection.temp_limit:
        cmds.append(f"rt_enable_templimit {1 if payload.temp_limit_enabled else 0}")
        cmds.append(put("rt_templimit_bottom", payload.temp_limit_bottom))
        cmds.append(put("rt_templimit_ceiling", payload.temp_limit_ceiling))

    if selection.miui_home_animation:
        cmds.append(put("miui_home_animation_rate", home_anim_value))

    if selection.recents_style:
        cmds.append(put_global("task_stack_view_layout_style", recents_style_value))

    if selection.background_blur_supported:
        blur_value = str(payload.background_blur_supported).strip().lower()
        if blur_value not in ("true", "false"):
            blur_value = "false"
        cmds.append(mqsas_setprop(f"persist.sys.background_blur_supported {blur_value}"))
    return cmds


class HyperTweakApp:
    def __init__(self) -> None:
        self.root = tb.Window(themename="darkly")
        self.root.title("HyperTweak")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        self._ui_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._adb_client: Any | None = None
        self._device: Any | None = None
        self._device_name: str | None = None

        self._build_ui()
        self._start_queue_poller()

    # -------------------------
    # UI
    # -------------------------
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

        # Scrollable modification area (left)
        # Extra right padding creates a gutter so the always-visible scrollbar
        # doesn't visually clash with section borders.
        self.scroller = ScrolledFrame(self.root, autohide=False, padding=(14, 8, 26, 10))
        self.scroller.grid(row=1, column=0, sticky="nsew")

        page = self.scroller
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        # Vars
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
        self.var_background_blur_supported = tk.StringVar(value="false")

        # Which sections should be applied
        self.apply_device_level_list = tk.BooleanVar(value=True)
        self.apply_computility = tk.BooleanVar(value=True)
        self.apply_advanced_visual_release = tk.BooleanVar(value=True)
        self.apply_temp_limit = tk.BooleanVar(value=False)
        self.apply_miui_home_animation = tk.BooleanVar(value=True)
        self.apply_recents_style = tk.BooleanVar(value=True)
        self.apply_background_blur_supported = tk.BooleanVar(value=True)

        # Current values (read from device)
        self.cur_device_level_list = tk.StringVar(value="—")
        self.cur_cpulevel = tk.StringVar(value="—")
        self.cur_gpulevel = tk.StringVar(value="—")
        self.cur_advanced_visual_release = tk.StringVar(value="—")
        self.cur_temp_limit_enabled = tk.StringVar(value="—")
        self.cur_temp_limit_bottom = tk.StringVar(value="—")
        self.cur_temp_limit_ceiling = tk.StringVar(value="—")
        self.cur_miui_home_animation_rate = tk.StringVar(value="—")
        self.cur_recents_style = tk.StringVar(value="—")
        self.cur_background_blur_supported = tk.StringVar(value="—")

        # Validation
        self._vcmd_int = (self.root.register(self._validate_int_entry), "%P")

        # Single-column layout inside scroll area
        content = ttk.Frame(page)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)

        r = 0
        r = self._section_current_values(content, r)
        r = self._section_device_levels(content, r)
        r = self._section_computility(content, r)
        r = self._section_advanced_visual_release(content, r)
        r = self._section_background_blur_supported(content, r)
        r = self._section_miui_home_animation(content, r)
        r = self._section_recents_style(content, r)
        r = self._section_temp_limit(content, r)

        # Apply (fixed, bottom; spans both columns)
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

        # Status log (right)
        log_wrap = ttk.Frame(self.root, padding=(10, 8, 14, 10), width=360)
        log_wrap.grid(row=1, column=1, sticky="nsew")
        self.root.rowconfigure(1, weight=1)
        log_wrap.rowconfigure(1, weight=1)
        log_wrap.grid_propagate(False)

        log_header = ttk.Frame(log_wrap)
        log_header.grid(row=0, column=0, sticky="ew")
        log_header.columnconfigure(0, weight=1)

        ttk.Label(log_header, text="Status Log").grid(row=0, column=0, sticky="w")
        self.btn_clear = ttk.Button(log_header, text="Clear", command=self._clear_log, width=10)
        self.btn_clear.grid(row=0, column=1, sticky="e")

        self.txt_log = tk.Text(
            log_wrap,
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
        log_wrap.columnconfigure(0, weight=1)

        self._log("Ready. Connect a device via USB debugging.")

    def _section_frame(self, parent: ttk.Widget, title: str) -> ttk.Labelframe:
        lf = ttk.Labelframe(parent, text=title, padding=(12, 10, 12, 10))
        # col 1 is a flexible spacer; inputs live in col 2 (right-aligned)
        lf.columnconfigure(1, weight=1)
        return lf

    def _titled_section(
        self,
        parent: ttk.Widget,
        title: str,
        enabled_var: tk.BooleanVar,
        after_toggle: Callable[[], None] | None = None,
    ) -> tuple[ttk.Labelframe, list[tuple[ttk.Widget, str]]]:
        lf = ttk.Labelframe(parent, padding=(12, 10, 12, 10))
        # col 1 is a flexible spacer; inputs live in col 2 (right-aligned)
        lf.grid_columnconfigure(1, weight=1)

        # Put checkbox+title into the Labelframe border label area (removes the notch/cut-in).
        label = ttk.Frame(lf)
        chk = ttk.Checkbutton(label, variable=enabled_var, text="")
        chk.pack(side="left", padx=(0, 6))
        ttk.Label(label, text=title, font=("Segoe UI", 10, "bold")).pack(side="left")
        lf.configure(labelwidget=label)

        widgets: list[tuple[ttk.Widget, str]] = []

        def on_toggle() -> None:
            self._set_section_enabled(widgets, bool(enabled_var.get()))
            if after_toggle is not None:
                after_toggle()

        chk.configure(command=on_toggle)
        return lf, widgets

    def _register_widget(
        self, widgets: list[tuple[ttk.Widget, str]], widget: ttk.Widget, enabled_state: str
    ) -> None:
        widgets.append((widget, enabled_state))

    def _set_section_enabled(self, widgets: list[tuple[ttk.Widget, str]], enabled: bool) -> None:
        for w, enabled_state in widgets:
            try:
                w.configure(state=(enabled_state if enabled else "disabled"))
            except tk.TclError:
                pass

    def _section_current_values(self, parent: ttk.Widget, row: int) -> int:
        lf = self._section_frame(parent, "Current Device Settings")
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        lf.columnconfigure(1, weight=1)

        btns = ttk.Frame(lf)
        btns.grid(row=0, column=0, sticky="w", columnspan=2, pady=(0, 8))

        ttk.Button(btns, text="Refresh from Device", command=self.refresh_current_settings).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(btns, text="Save", command=self.save_current_settings).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )
        ttk.Button(btns, text="Load", command=self.load_current_settings).grid(
            row=0, column=2, sticky="w", padx=(10, 0)
        )

        def add(r: int, label: str, var: tk.StringVar) -> None:
            ttk.Label(lf, text=label).grid(row=r, column=0, sticky="w", padx=(0, 10))
            ttk.Label(lf, textvariable=var, foreground="#c9d1d9").grid(row=r, column=1, sticky="w")

        r = 1
        add(r, "deviceLevelList", self.cur_device_level_list); r += 1
        add(r, "cpulevel", self.cur_cpulevel); r += 1
        add(r, "gpulevel", self.cur_gpulevel); r += 1
        add(r, "advanced_visual_release", self.cur_advanced_visual_release); r += 1
        add(r, "background_blur_supported", self.cur_background_blur_supported); r += 1
        add(r, "miui_home_animation_rate", self.cur_miui_home_animation_rate); r += 1
        add(r, "task_stack_view_layout_style", self.cur_recents_style); r += 1
        add(r, "rt_enable_templimit", self.cur_temp_limit_enabled); r += 1
        add(r, "rt_templimit_bottom", self.cur_temp_limit_bottom); r += 1
        add(r, "rt_templimit_ceiling", self.cur_temp_limit_ceiling); r += 1
        # temp limit at the end, per UI order
        
        return row + 1

    def _section_device_levels(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(parent, "Device Level List", self.apply_device_level_list)
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        v_cb = self._add_combo(lf, "v", self.var_v, values=[1, 2, 3], r=0)
        c_cb = self._add_combo(lf, "c", self.var_c, values=[1, 2, 3], r=1)
        g_cb = self._add_combo(lf, "g", self.var_g, values=[1, 2, 3], r=2)
        self._register_widget(widgets, v_cb, "readonly")
        self._register_widget(widgets, c_cb, "readonly")
        self._register_widget(widgets, g_cb, "readonly")
        self._set_section_enabled(widgets, bool(self.apply_device_level_list.get()))
        return row + 1

    def _section_computility(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(parent, "Computility", self.apply_computility)
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        cpu_cb = self._add_combo(lf, "cpulevel", self.var_cpulevel, values=list(range(1, 7)), r=0)
        gpu_cb = self._add_combo(lf, "gpulevel", self.var_gpulevel, values=list(range(1, 7)), r=1)
        self._register_widget(widgets, cpu_cb, "readonly")
        self._register_widget(widgets, gpu_cb, "readonly")
        self._set_section_enabled(widgets, bool(self.apply_computility.get()))
        return row + 1

    def _section_advanced_visual_release(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(
            parent, "Advanced Visual Release", self.apply_advanced_visual_release
        )
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        avr_cb = self._add_combo(
            lf,
            "Advanced Visual Release",
            self.var_advanced_visual_release,
            values=[1, 2, 3],
            r=0,
        )
        self._register_widget(widgets, avr_cb, "readonly")
        self._set_section_enabled(widgets, bool(self.apply_advanced_visual_release.get()))
        return row + 1

    def _section_temp_limit(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(
            parent, "Temp Limit", self.apply_temp_limit, after_toggle=self._sync_temp_enabled_state
        )
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        chk = ttk.Checkbutton(
            lf,
            text="Enable",
            variable=self.var_temp_enable,
            command=self._sync_temp_enabled_state,
        )
        chk.grid(row=0, column=0, sticky="w", columnspan=2, pady=(0, 8))
        self._register_widget(widgets, chk, "normal")

        ttk.Label(lf, text="Bottom").grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.ent_temp_bottom = ttk.Entry(
            lf,
            textvariable=self.var_temp_bottom,
            validate="key",
            validatecommand=self._vcmd_int,
            width=18,
            bootstyle="secondary",
        )
        self.ent_temp_bottom.grid(row=1, column=2, sticky="e")
        self._register_widget(widgets, self.ent_temp_bottom, "normal")

        ttk.Label(lf, text="Ceiling").grid(row=2, column=0, sticky="w", pady=(6, 0), padx=(0, 10))
        self.ent_temp_ceiling = ttk.Entry(
            lf,
            textvariable=self.var_temp_ceiling,
            validate="key",
            validatecommand=self._vcmd_int,
            width=18,
            bootstyle="secondary",
        )
        self.ent_temp_ceiling.grid(row=2, column=2, sticky="e", pady=(6, 0))
        self._register_widget(widgets, self.ent_temp_ceiling, "normal")
        self._set_section_enabled(widgets, bool(self.apply_temp_limit.get()))
        self._sync_temp_enabled_state()
        return row + 1

    def _section_miui_home_animation(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(
            parent, "MIUI Home Animation", self.apply_miui_home_animation
        )
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        anim_cb = self._add_combo(
            lf,
            "Animation",
            self.var_home_anim,
            values=["Relaxed", "Balanced", "Fast"],
            r=0,
        )
        self._register_widget(widgets, anim_cb, "readonly")
        self._set_section_enabled(widgets, bool(self.apply_miui_home_animation.get()))
        return row + 1

    def _section_recents_style(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(parent, "Recents Style", self.apply_recents_style)
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        rec_cb = self._add_combo(
            lf,
            "Recents",
            self.var_recents_style,
            values=["Vertically", "Horizontally", "Stacked"],
            r=0,
        )
        self._register_widget(widgets, rec_cb, "readonly")
        self._set_section_enabled(widgets, bool(self.apply_recents_style.get()))
        return row + 1

    def _section_background_blur_supported(self, parent: ttk.Widget, row: int) -> int:
        lf, widgets = self._titled_section(
            parent, "Background Blur Support", self.apply_background_blur_supported
        )
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        blur_cb = self._add_combo(
            lf,
            "background_blur_supported",
            self.var_background_blur_supported,
            values=["true", "false"],
            r=0,
        )
        self._register_widget(widgets, blur_cb, "readonly")
        self._set_section_enabled(widgets, bool(self.apply_background_blur_supported.get()))
        return row + 1

    def _add_combo(
        self,
        parent: ttk.Widget,
        label: str,
        var: tk.Variable,
        values: list[Any],
        r: int,
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(
            row=r, column=0, sticky="w", pady=(0 if r == 0 else 6, 0), padx=(0, 10)
        )
        cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=18)
        cb.configure(bootstyle="secondary")
        cb.grid(row=r, column=2, sticky="e", pady=(0 if r == 0 else 6, 0))
        return cb

    def _sync_temp_enabled_state(self) -> None:
        # If the whole section is disabled, keep entries locked regardless of the inner toggle.
        if not bool(self.apply_temp_limit.get()):
            try:
                self.ent_temp_bottom.configure(state="disabled")
                self.ent_temp_ceiling.configure(state="disabled")
            except tk.TclError:
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
            # Common on Windows when the ADB server isn't running: WinError 10061
            if getattr(e, "winerror", None) == 10061:
                self._log_async("ADB server not running. Attempting to start it...")
                self._ensure_adb_server_running_bg()
                # Retry once
                devices = client.devices()
            else:
                raise

        if not devices:
            raise RuntimeError("No devices found. Ensure USB debugging is enabled and run `adb devices`.")

        device = devices[0]
        serial = getattr(device, "serial", "<unknown>")

        # Quick sanity check
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
        adb: str | None = None

        # Prefer a bundled platform-tools/adb.exe next to the executable (PyInstaller onedir).
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidate = os.path.join(exe_dir, "platform-tools", "adb.exe")
            if os.path.exists(candidate):
                adb = candidate

        # When running from source, allow a local platform-tools folder too.
        if not adb:
            candidate = os.path.join(os.path.dirname(__file__), "platform-tools", "adb.exe")
            if os.path.exists(candidate):
                adb = candidate

        # Finally, fall back to PATH.
        if not adb:
            adb = shutil.which("adb")

        if not adb:
            raise RuntimeError(
                "ADB not found. Put platform-tools next to the app (platform-tools/adb.exe) "
                "or install Android platform-tools and ensure `adb` is in PATH."
            )

        # Start server; if it's already running, adb prints a benign message.
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
            "deviceLevelList": self.cur_device_level_list.get(),
            "cpulevel": self.cur_cpulevel.get(),
            "gpulevel": self.cur_gpulevel.get(),
            "advanced_visual_release": self.cur_advanced_visual_release.get(),
            "rt_enable_templimit": self.cur_temp_limit_enabled.get(),
            "rt_templimit_bottom": self.cur_temp_limit_bottom.get(),
            "rt_templimit_ceiling": self.cur_temp_limit_ceiling.get(),
            "miui_home_animation_rate": self.cur_miui_home_animation_rate.get(),
            "task_stack_view_layout_style": self.cur_recents_style.get(),
            "background_blur_supported": self.cur_background_blur_supported.get(),
        }

    def save_current_settings(self) -> None:
        snapshot = self._current_snapshot()

        default_name = "hypertweak_settings.json"
        if self._device_name:
            safe = re.sub(r'[<>:"/\\\\|?*\\n\\r\\t]', "_", self._device_name).strip()
            safe = re.sub(r"\\s+", " ", safe)
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
                    if vlow in ("0", "false"):
                        self.var_background_blur_supported.set("false")
                        applied += 1
                    elif vlow in ("1", "true"):
                        self.var_background_blur_supported.set("true")
                        applied += 1

            self._log(f"Loaded {applied} value(s) from: {path}", level="success")
        except Exception as e:
            self._log(f"Load failed: {e}", level="error")

    def _refresh_current_settings_bg(self) -> None:
        assert self._device is not None

        queries: list[tuple[str, str]] = [
            ("deviceLevelList", "settings get system deviceLevelList"),
            ("cpulevel", "getprop persist.sys.computility.cpulevel"),
            ("gpulevel", "getprop persist.sys.computility.gpulevel"),
            ("advanced_visual_release", "getprop persist.sys.advanced_visual_release"),
            ("rt_enable_templimit", "settings get system rt_enable_templimit"),
            ("rt_templimit_bottom", "settings get system rt_templimit_bottom"),
            ("rt_templimit_ceiling", "settings get system rt_templimit_ceiling"),
            ("miui_home_animation_rate", "settings get system miui_home_animation_rate"),
            ("task_stack_view_layout_style", "settings get global task_stack_view_layout_style"),
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
    # Background execution + logging
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
                        self._apply_current_kv(msg)
                    elif kind == "busy":
                        busy = msg == "1"
                        self.btn_connect.configure(state=("disabled" if busy else "normal"))
                        self.btn_reboot.configure(state=("disabled" if busy else "normal"))
                        self.btn_apply.configure(state=("disabled" if busy else "normal"))
            except queue.Empty:
                pass
            self.root.after(120, poll)

        self.root.after(120, poll)

    def _apply_current_kv(self, kv: str) -> None:
        if "=" not in kv:
            return
        key, val = kv.split("=", 1)
        key = key.strip()
        val = val.strip()

        if key == "deviceLevelList":
            self.cur_device_level_list.set(val)
            # Best-effort parse so dropdowns reflect device state
            m = re.search(r"v:(\d+)\s*,\s*c:(\d+)\s*[.,]\s*g:(\d+)", val)
            if m:
                try:
                    self.var_v.set(int(m.group(1)))
                    self.var_c.set(int(m.group(2)))
                    self.var_g.set(int(m.group(3)))
                except Exception:
                    pass
            return

        mapping: dict[str, tk.StringVar] = {
            "cpulevel": self.cur_cpulevel,
            "gpulevel": self.cur_gpulevel,
            "advanced_visual_release": self.cur_advanced_visual_release,
            "rt_enable_templimit": self.cur_temp_limit_enabled,
            "rt_templimit_bottom": self.cur_temp_limit_bottom,
            "rt_templimit_ceiling": self.cur_temp_limit_ceiling,
            "miui_home_animation_rate": self.cur_miui_home_animation_rate,
            "task_stack_view_layout_style": self.cur_recents_style,
            "background_blur_supported": self.cur_background_blur_supported,
        }
        if key in mapping:
            mapping[key].set(val)

        # Best-effort sync into inputs where it makes sense
        if key == "cpulevel" and val.isdigit():
            self.var_cpulevel.set(int(val))
        elif key == "gpulevel" and val.isdigit():
            self.var_gpulevel.set(int(val))
        elif key == "advanced_visual_release" and val.isdigit():
            self.var_advanced_visual_release.set(int(val))
        elif key == "rt_enable_templimit":
            self.var_temp_enable.set(val in ("1", "true", "True", "enabled", "on", "ON"))
            self._sync_temp_enabled_state()
        elif key == "rt_templimit_bottom" and val.isdigit():
            self.var_temp_bottom.set(val)
        elif key == "rt_templimit_ceiling" and val.isdigit():
            self.var_temp_ceiling.set(val)
        elif key == "miui_home_animation_rate":
            home_anim_reverse = {"0": "Relaxed", "1": "Balanced", "2": "Fast"}
            if val in home_anim_reverse:
                self.var_home_anim.set(home_anim_reverse[val])
            elif val in ("Relaxed", "Balanced", "Fast"):
                self.var_home_anim.set(val)
        elif key == "task_stack_view_layout_style":
            recents_style_reverse = {"0": "Vertically", "1": "Horizontally", "2": "Stacked"}
            if val in recents_style_reverse:
                self.var_recents_style.set(recents_style_reverse[val])
            elif val in ("Vertically", "Horizontally", "Stacked"):
                self.var_recents_style.set(val)
        elif key == "background_blur_supported":
            vlow = val.lower()
            if vlow in ("0", "false"):
                self.var_background_blur_supported.set("false")
            elif vlow in ("1", "true"):
                self.var_background_blur_supported.set("true")

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

    # -------------------------
    # Validation
    # -------------------------
    def _validate_int_entry(self, proposed: str) -> bool:
        if proposed == "":
            return True
        return proposed.isdigit()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    HyperTweakApp().run()
