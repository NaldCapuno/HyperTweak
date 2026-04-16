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
    AdbClient = None

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
    IGNORED_KEYS = {
        "boot_count", "Phenotype_boot_count", "batterystats_reset_time", 
        "last_update", "FBO_UPLOAD_TIME", "pc_security_center_last_fully_charge_time",
        "start_time_of_self_detection", "freeform_timestamps", "network_watchlist_last_report_time",
        "key_persist_cumulative_playback_ms", "key_persist_notification_date", "pay_session_id",
        "screen_brightness", "screen_brightness_mode", "next_alarm_formatted", "is_custom_shortcut_effective",
        "volume_music_headset", "volume_voice_headset", "volume_voice_speaker", "should_filter_toolbox",
        "last_change_dual_clock_enable", "key_garbage_danger_in_size", "key_garbage_deepclean_size",
        "key_garbage_installed_app_count", "key_garbage_normal_size", "key_garbage_not_used_app_count",
        "key_score_in_security", "key_minus_score_in_security_exclude_virus", "update_uidlist_to_sla",
        "constant_lockscreen_info", "KEY_FBO_DATA", "FBO_UPLOAD_LIST", "sidebar_bounds",
        "LAST_INIT_POSITION", "am_show_system_apps", "enabled_input_methods", "media_button_receiver",
        "provision_immersive_enable", "restart_nap_after_start", "xspace_enabled", "5g_icon_group_mode0",
        "adb_allowed_connection_time", "is_timeout_for_settings_search", "private_dns_mode", 
        "xiaomi_mi_play_last_playing_package_name"
    }

    def __init__(self) -> None:
        self.root = tb.Window(themename="darkly")
        self.root.title("HyperTweak")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        self._ui_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._adb_client: Any | None = None
        self._device: Any | None = None
        self._device_name: str | None = None
        self._search_settings_after_id: str | None = None
        self._settings_full_text: dict[str, str] = {
            "system": "",
            "secure": "",
            "global": "",
            "props": "",
        }

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
        self._install_current_device_settings_wheel_fix()
        r = build_quick_toggles(content, self, r)
        r = build_advanced_settings(content, self, r)
        self._boost_left_panel_wheel_speed()
        self._install_left_panel_wheel_reapply()

        footer = ttk.Frame(self.root, padding=(14, 6, 14, 8))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.columnconfigure(0, weight=1)

        btns = ttk.Frame(footer)
        btns.grid(row=0, column=0, sticky="ew")
        btns.columnconfigure(0, weight=0)
        btns.columnconfigure(1, weight=0)
        btns.columnconfigure(2, weight=1)

        self.btn_restore_previous = ttk.Button(
            btns,
            text="Restore previous settings",
            command=self.restore_previous_settings,
            style="secondary.TButton",
            width=22,
        )
        self.btn_restore_previous.grid(row=0, column=0, sticky="w")
        self.btn_restore_previous.grid_remove()

        self.btn_view_previous = ttk.Button(
            btns,
            text="View previous settings",
            command=self.view_previous_settings,
            style="secondary.TButton",
            width=20,
        )
        self.btn_view_previous.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.btn_view_previous.grid_remove()

        self.btn_apply = ttk.Button(
            btns,
            text="Apply Settings",
            command=self.apply_settings,
            style="success.TButton",
            width=18,
        )
        self.btn_apply.grid(row=0, column=2, sticky="e")

        self.btn_reboot = ttk.Button(
            btns,
            text="Reboot",
            command=self.reboot_device,
            style="danger.TButton",
            width=10,
        )
        self.btn_reboot.grid(row=0, column=3, sticky="e", padx=(10, 0))

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
        self.root.after_idle(self._run_search_settings_refresh)

    def _install_current_device_settings_wheel_fix(self) -> None:
        wheel_unit_multiplier = 3

        def _scroll_widget(widget: Any, units: int) -> str:
            try:
                widget.yview_scroll(units * wheel_unit_multiplier, "units")
            except Exception:
                pass
            return "break"

        def _on_mousewheel(e: Any) -> str:
            w = getattr(e, "widget", None)
            delta = int(getattr(e, "delta", 0) or 0)
            if w is None or delta == 0:
                return "break"
            steps = max(1, int(abs(delta) / 120))
            units = -steps if delta > 0 else steps
            return _scroll_widget(w, units)

        def _on_button4(e: Any) -> str:
            w = getattr(e, "widget", None)
            return _scroll_widget(w, -1) if w is not None else "break"

        def _on_button5(e: Any) -> str:
            w = getattr(e, "widget", None)
            return _scroll_widget(w, 1) if w is not None else "break"

        self.root.bind_class("HyperTweakSettingsText", "<MouseWheel>", _on_mousewheel, add="+")
        self.root.bind_class("HyperTweakSettingsText", "<Button-4>", _on_button4, add="+")
        self.root.bind_class("HyperTweakSettingsText", "<Button-5>", _on_button5, add="+")

        def _scroll_from_scrollbar_event(e: Any, units: int) -> str:
            mapping = getattr(self, "current_settings_scroll_target_by_widget", {}) or {}
            w = getattr(e, "widget", None)
            key = str(w) if w is not None else ""
            target = mapping.get(key)
            if target is None:
                return "break"
            try:
                target.yview_scroll(units * 3, "units")
            except Exception:
                pass
            return "break"

        def _on_scrollbar_mousewheel(e: Any) -> str:
            delta = int(getattr(e, "delta", 0) or 0)
            if delta == 0:
                return "break"
            steps = max(1, int(abs(delta) / 120))
            units = -steps if delta > 0 else steps
            return _scroll_from_scrollbar_event(e, units)

        def _on_scrollbar_button4(e: Any) -> str:
            return _scroll_from_scrollbar_event(e, -1)

        def _on_scrollbar_button5(e: Any) -> str:
            return _scroll_from_scrollbar_event(e, 1)

        self.root.bind_class(
            "HyperTweakSettingsScrollbar", "<MouseWheel>", _on_scrollbar_mousewheel, add="+"
        )
        self.root.bind_class(
            "HyperTweakSettingsScrollbar", "<Button-4>", _on_scrollbar_button4, add="+"
        )
        self.root.bind_class(
            "HyperTweakSettingsScrollbar", "<Button-5>", _on_scrollbar_button5, add="+"
        )

    def _boost_left_panel_wheel_speed(self) -> None:
        scroller = getattr(self, "scroller", None)
        if scroller is None:
            return

        exclude_targets = set(getattr(self, "current_settings_wheel_exclude", []) or [])
        exclude_targets.discard(None)
        wheel_unit_multiplier = 3

        def _scroll_scroller(units: int) -> str:
            try:
                scroller.yview_scroll(units * wheel_unit_multiplier, "units")
            except Exception:
                pass
            return "break"

        def _on_mousewheel(e: Any) -> str:
            delta = int(getattr(e, "delta", 0) or 0)
            if delta == 0:
                return "break"
            steps = max(1, int(abs(delta) / 120))
            units = -steps if delta > 0 else steps
            return _scroll_scroller(units)

        def _on_button4(_e: Any) -> str:
            return _scroll_scroller(-1)

        def _on_button5(_e: Any) -> str:
            return _scroll_scroller(1)

        def _bind_iterative(root_widget: Any) -> None:
            stack: list[Any] = [root_widget]
            visited: set[str] = set()
            while stack:
                widget = stack.pop()
                wname = str(getattr(widget, "_w", ""))
                if wname in visited:
                    continue
                visited.add(wname)

                if widget not in exclude_targets:
                    widget.bind("<MouseWheel>", _on_mousewheel)
                    widget.bind("<Button-4>", _on_button4)
                    widget.bind("<Button-5>", _on_button5)

                try:
                    children = list(widget.winfo_children())
                except Exception:
                    children = []
                stack.extend(children)

        _bind_iterative(scroller)
        container = getattr(scroller, "container", None)
        if container is not None:
            _bind_iterative(container)

    def _install_left_panel_wheel_reapply(self) -> None:
        if getattr(self, "_left_panel_wheel_reapply_installed", False):
            return
        scroller = getattr(self, "scroller", None)
        container = getattr(scroller, "container", None) if scroller is not None else None
        if container is None:
            return

        def _reapply(_e: Any) -> None:
            self.root.after_idle(self._boost_left_panel_wheel_speed)

        container.bind("<Enter>", _reapply, add="+")
        self._left_panel_wheel_reapply_installed = True

    def _init_vars(self) -> None:
        self.var_v = tk.IntVar(value=1)
        self.var_c = tk.IntVar(value=1)
        self.var_g = tk.IntVar(value=1)
        self.var_cpulevel = tk.IntVar(value=1)
        self.var_gpulevel = tk.IntVar(value=1)
        self.var_advanced_visual_release = tk.IntVar(value=1)
        self.var_temp_enable = tk.BooleanVar(value=False)
        self.var_temp_bottom = tk.StringVar(value="42")
        self.var_temp_ceiling = tk.StringVar(value="45")
        self.var_home_anim = tk.StringVar(value="Balanced")
        self.var_recents_style = tk.StringVar(value="Vertically")
        self.var_background_blur_supported = tk.StringVar(value="Disabled")

        self.apply_device_level_list = tk.BooleanVar(value=True)
        self.apply_computility = tk.BooleanVar(value=True)
        self.apply_advanced_visual_release = tk.BooleanVar(value=True)
        self.apply_temp_limit = tk.BooleanVar(value=False)
        self.apply_miui_home_animation = tk.BooleanVar(value=True)
        self.apply_recents_style = tk.BooleanVar(value=False) 
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

        snap = self._snapshot_advanced_settings_bg()
        for key, val in snap.items():
            if val is None:
                continue
            self._ui_queue.put(("current", f"{key}={val}"))

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
        values: dict[str, str] = {}
        for name in ("system", "secure", "global", "props"):
            values[name] = self._settings_full_text.get(name, "")
        return values

    def _searchable_settings_tables(self) -> list[tuple[str, Any]]:
        tables: list[tuple[str, Any]] = []
        for ns, attr in (
            ("system", "txt_settings_system"),
            ("secure", "txt_settings_secure"),
            ("global", "txt_settings_global"),
            ("props", "txt_settings_props"),
        ):
            txt = getattr(self, attr, None)
            if txt is not None:
                tables.append((ns, txt))
        return tables

    def _set_settings_table_text(self, ns: str, content: str) -> None:
        txt = getattr(self, f"txt_settings_{ns}", None)
        if txt is None:
            return
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("1.0", content)
        txt.configure(state="disabled")

    def _filter_settings_lines_by_key(self, content: str, query: str) -> tuple[str, int]:
        qlow = query.lower()
        matches: list[str] = []
        for line in content.splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            key = line_stripped.split(" = ", 1)[0].strip()
            if qlow in key.lower():
                matches.append(line_stripped)
        return "\n".join(matches), len(matches)

    def _schedule_search_settings_refresh(self, _event: object | None = None) -> None:
        aid = self._search_settings_after_id
        if aid is not None:
            try:
                self.root.after_cancel(aid)
            except Exception:
                pass
            self._search_settings_after_id = None
        self._search_settings_after_id = self.root.after(200, self._run_search_settings_refresh)

    def _run_search_settings_refresh(self) -> None:
        self._search_settings_after_id = None
        ent = getattr(self, "ent_search_settings", None)
        query = (ent.get().strip() if ent is not None else "").strip()

        tab_order = ("system", "secure", "global", "props")

        if not query:
            for ns in tab_order:
                self._set_settings_table_text(ns, self._settings_full_text.get(ns, ""))
            return

        match_counts: dict[str, int] = {}
        for ns in tab_order:
            full_content = self._settings_full_text.get(ns, "")
            filtered_content, count = self._filter_settings_lines_by_key(full_content, query)
            match_counts[ns] = count
            self._set_settings_table_text(ns, filtered_content if filtered_content else "No matching settings.")

        nb = getattr(self, "nb_current_settings", None)
        tab_index = getattr(self, "current_settings_tab_index", {})
        if nb is not None and isinstance(tab_index, dict):
            for ns in tab_order:
                if match_counts.get(ns, 0) > 0 and ns in tab_index:
                    nb.select(tab_index[ns])
                    break

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

            tabs = {
                "system": "txt_settings_system",
                "secure": "txt_settings_secure",
                "global": "txt_settings_global",
                "props": "txt_settings_props",
            }
            for key, attr in tabs.items():
                txt = getattr(self, attr, None)
                if txt is None or key not in values:
                    continue
                content = str(values.get(key, ""))
                self._settings_full_text[key] = content
                self._set_settings_table_text(key, content)

            self._log(f"Loaded settings from: {path}", level="success")
            self._schedule_search_settings_refresh()

            if self._device:
                self._run_bg("auto_diff", lambda: self._check_diff_only_bg(values))
            else:
                self._log("Connect a device to see differences between file and device.", level="error")

        except Exception as e:
            self._log(f"Load failed: {e}", level="error")

    def _check_diff_only_bg(self, loaded_values: dict[str, str]) -> None:
        assert self._device is not None
        self._log_async("Comparing loaded file with device state...")
        
        diff_count = 0
        namespaces = ["system", "secure", "global"]
        
        for ns in namespaces:
            if ns not in loaded_values: continue
            
            raw_live = self._device.shell(f"settings list {ns}") or ""
            live_map = {}
            for line in raw_live.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    live_map[k.strip()] = v.strip()

            for line in loaded_values[ns].splitlines():
                if " = " in line:
                    k, v = line.split(" = ", 1)
                    k, v = k.strip(), v.strip()

                    if k in self.IGNORED_KEYS:
                       continue
                    
                    live_val = live_map.get(k)
                    if live_val != v:
                        self._log_async(f"[DIFF] {ns} -> {k}: Device is '{live_val}', File is '{v}'")
                        diff_count += 1

        if "props" in loaded_values:
            for line in loaded_values["props"].splitlines():
                if " = " in line:
                    k, v = [x.strip() for x in line.split(" = ", 1)]
                    if k in self.IGNORED_KEYS: continue
                    
                    live_prop = self._device.shell(f"getprop {k}").strip()
                    if live_prop != v:
                        self._log_async(f"[DIFF] props -> {k}: Device is '{live_prop}', File is '{v}'")
                        diff_count += 1

        if diff_count > 0:
            self._log_async(f"Found {diff_count} differences. Click 'Apply Loaded' to sync.", level="info")
        else:
            self._log_async("Device is already perfectly in sync with this file.", level="success")

    def _refresh_current_settings_bg(self) -> None:
        assert self._device is not None
        tables: list[tuple[str, str]] = [
            ("system", "settings list system"),
            ("secure", "settings list secure"),
            ("global", "settings list global"),
            ("props", "getprop"),
        ]
        self._log_async("Refreshing settings (system/secure/global) and props from device...")
        for table, cmd in tables:
            raw = self._device.shell(cmd) or ""
            lines: list[str] = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                if table == "props":
                    # Typical getprop line: [key]: [value]
                    if line.startswith("[") and "]" in line:
                        try:
                            key_part, val_part = line.split("]:", 1)
                            key = key_part.lstrip("[").strip()
                            val = val_part.strip()
                            if val.startswith("[") and val.endswith("]"):
                                val = val[1:-1].strip()
                            lines.append(f"{key} = {val}")
                        except Exception:
                            lines.append(line)
                    else:
                        lines.append(line)
                else:
                    if "=" in line:
                        k, v = line.split("=", 1)
                        lines.append(f"{k} = {v}")
                    else:
                        lines.append(line)
            formatted = "\n".join(lines) or "No settings returned."
            self._ui_queue.put((f"settings_{table}", formatted))
        self._log_async("Refresh complete.", level="success")

    # -------------------------
    # Apply Settings
    # -------------------------
    def apply_loaded_diff(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        
        target_data = self._current_snapshot()
        self._run_bg("gather_diffs", lambda: self._gather_diffs_for_ui(target_data))

    def _gather_diffs_for_ui(self, target_data: dict[str, str]) -> None:
        assert self._device is not None
        diff_list = []
        namespaces = ["system", "secure", "global"]

        for ns in namespaces:
            if ns not in target_data: 
                continue
                
            raw_live = self._device.shell(f"settings list {ns}") or ""
            live_map = {}
            for line in raw_live.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    live_map[k.strip()] = v.strip()

            for line in target_data[ns].splitlines():
                if " = " in line:
                    parts = [x.strip() for x in line.split(" = ", 1)]
                    if len(parts) < 2: continue
                    k, v = parts[0], parts[1]
                    
                    if k in self.IGNORED_KEYS: 
                        continue
                    
                    live_val = live_map.get(k)
                    
                    if live_val != v:
                        diff_list.append((ns, k, live_val, v))

        if "props" in target_data:
            self._log_async("Verifying system properties...")
            for line in target_data["props"].splitlines():
                if " = " in line:
                    k, v = [x.strip() for x in line.split(" = ", 1)]
                    
                    if k in self.IGNORED_KEYS:
                        continue
                        
                    live_prop = self._device.shell(f"getprop {k}").strip()
                    
                    if live_prop != v:
                        diff_list.append(("props", k, live_prop, v))

        if not diff_list:
            self._log_async("No significant differences found to apply.", level="success")
            return

        from ui.diff_selector import DiffSelectionWindow
        self.root.after(0, lambda: DiffSelectionWindow(self.root, diff_list, self._apply_selected_items))

    def _apply_selected_items(self, selected_items: list[tuple[str, str, str, str]]) -> None:
        self._run_bg("apply_selected", lambda: self._apply_selected_bg(selected_items))

    def _apply_selected_bg(self, items: list[tuple[str, str, str, str]]) -> None:
        assert self._device is not None
        from config import get_mqsas_command
        
        self._log_async(f"Applying {len(items)} selected change(s)...")
        started = time.time()
        
        for ns, k, _, v in items:
            try:
                if ns == "props":
                    self._device.shell(get_mqsas_command(k, v))
                else:
                    self._device.shell(f"settings put {ns} {k} {v}")
                
                self._log_async(f"[OK] {ns} -> {k} = {v}")
            except Exception as e:
                self._log_async(f"[!] Failed to apply {k}: {e}", level="error")

        elapsed_ms = int((time.time() - started) * 1000)
        self._log_async(f"Apply complete in {elapsed_ms} ms.", level="success")
        if any(item[0] == "props" for item in items):
            self._log_async("Note: Some property changes require a reboot to take effect.")

    def _apply_diff_bg(self, target_data: dict[str, str]) -> None:
        assert self._device is not None
        self._log_async("Starting Smart Sync (comparing differences)...")
        
        changes_count = 0
        namespaces = ["system", "secure", "global"]
        
        for ns in namespaces:
            if ns not in target_data: continue
            
            raw_live = self._device.shell(f"settings list {ns}") or ""
            live_map = {}
            for line in raw_live.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    live_map[k.strip()] = v.strip()

            for line in target_data[ns].splitlines():
                if " = " in line:
                    k, v = line.split(" = ", 1)
                    k, v = k.strip(), v.strip()
                    
                    if live_map.get(k) != v:
                        self._log_async(f"Updating {ns}: {k} = {v}")
                        self._device.shell(f"settings put {ns} {k} {v}")
                        changes_count += 1

        if "props" in target_data:
            for line in target_data["props"].splitlines():
                if " = " in line:
                    k, v = line.split(" = ", 1)
                    k, v = k.strip(), v.strip()

                    from config import get_mqsas_command
                    self._device.shell(get_mqsas_command(k, v))
                    changes_count += 1

        if changes_count > 0:
            self._log_async(f"Smart Sync complete. Applied {changes_count} changes.", level="success")
        else:
            self._log_async("No differences found. Device is already in sync.", level="success")

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
        self._run_bg("apply", lambda: self._apply_with_snapshot_bg(payload, selection))

    def _snapshot_advanced_settings_bg(self) -> dict[str, str]:
        assert self._device is not None
        snap: dict[str, str] = {}

        def sh(cmd: str) -> str:
            try:
                return (self._device.shell(cmd) or "").strip()
            except Exception:
                return ""

        # Animation scales (used by "Remove animations" quick toggle and current settings)
        snap["window_animation_scale"] = sh("settings get global window_animation_scale")
        snap["transition_animation_scale"] = sh("settings get global transition_animation_scale")
        snap["animator_duration_scale"] = sh("settings get global animator_duration_scale")

        snap["deviceLevelList"] = sh("settings get system deviceLevelList")
        snap["cpulevel"] = sh("getprop persist.sys.computility.cpulevel")
        snap["gpulevel"] = sh("getprop persist.sys.computility.gpulevel")
        snap["advanced_visual_release"] = sh("getprop persist.sys.advanced_visual_release")
        snap["rt_enable_templimit"] = sh("settings get system rt_enable_templimit")
        snap["rt_templimit_bottom"] = sh("settings get system rt_templimit_bottom")
        snap["rt_templimit_ceiling"] = sh("settings get system rt_templimit_ceiling")
        snap["miui_home_animation_rate"] = sh("settings get system miui_home_animation_rate")
        snap["task_stack_view_layout_style"] = sh(
            "settings get global task_stack_view_layout_style"
        )
        snap["background_blur_supported"] = sh("getprop persist.sys.background_blur_supported")

        # Infer current "Remove animations" state: consider disabled if all three scales are 0 / 0.0
        try:
            wa = snap.get("window_animation_scale", "").strip()
            ta = snap.get("transition_animation_scale", "").strip()
            aa = snap.get("animator_duration_scale", "").strip()
            def _is_zero(x: str) -> bool:
                return x in ("0", "0.0")
            disabled_now = _is_zero(wa) and _is_zero(ta) and _is_zero(aa)
            self._animations_disabled = disabled_now
            self._ui_queue.put(
                (
                    "anim_btn_text",
                    "Enable animations" if disabled_now else "Disable animations",
                )
            )
        except Exception:
            pass

        return snap

    def _payload_from_snapshot(self, snap: dict[str, str]) -> SettingsPayload:
        v = c = g = 1
        dvl = (snap.get("deviceLevelList") or "").strip()
        m = re.search(r"v:(\d+)\s*,\s*c:(\d+)\s*[.,]\s*g:(\d+)", dvl)
        if m:
            try:
                v = int(m.group(1))
                c = int(m.group(2))
                g = int(m.group(3))
            except Exception:
                pass

        def as_int(key: str, default: int = 0) -> int:
            raw = (snap.get(key) or "").strip()
            return int(raw) if raw.isdigit() else default

        def as_bool(key: str) -> bool:
            raw = (snap.get(key) or "").strip().lower()
            return raw in ("1", "true", "enabled", "on", "yes")

        home_anim_reverse = {"0": "Relaxed", "1": "Balanced", "2": "Fast"}
        home_raw = (snap.get("miui_home_animation_rate") or "").strip()
        home = home_anim_reverse.get(home_raw, home_raw or "Balanced")

        blur_raw = (snap.get("background_blur_supported") or "").strip().lower()
        blur = "Enabled" if blur_raw in ("1", "true", "enabled", "on", "yes") else "Disabled"

        return SettingsPayload(
            v=v,
            c=c,
            g=g,
            cpulevel=as_int("cpulevel", 3),
            gpulevel=as_int("gpulevel", 3),
            advanced_visual_release=as_int("advanced_visual_release", 1),
            temp_limit_enabled=as_bool("rt_enable_templimit"),
            temp_limit_bottom=as_int("rt_templimit_bottom", 35),
            temp_limit_ceiling=as_int("rt_templimit_ceiling", 45),
            miui_home_animation=home,
            recents_style="Vertically",
            background_blur_supported=blur,
        )

    def _apply_with_snapshot_bg(self, payload: SettingsPayload, selection: ApplySelection) -> None:
        assert self._device is not None
        self._log_async("Saving current Advanced Settings snapshot...")
        self._previous_advanced_snapshot = self._snapshot_advanced_settings_bg()
        self._previous_advanced_selection = selection
        self._log_async("Snapshot saved.", level="success")
        try:
            self._apply_settings_bg(payload, selection)
        finally:
            if getattr(self, "_previous_advanced_snapshot", None):
                self._ui_queue.put(("show_restore_previous", "1"))

    def _populate_inputs_from_payload(self, payload: SettingsPayload) -> None:
        self.var_v.set(int(payload.v))
        self.var_c.set(int(payload.c))
        self.var_g.set(int(payload.g))
        self.var_cpulevel.set(int(payload.cpulevel))
        self.var_gpulevel.set(int(payload.gpulevel))
        self.var_advanced_visual_release.set(int(payload.advanced_visual_release))
        self.var_temp_enable.set(bool(payload.temp_limit_enabled))
        self.var_temp_bottom.set(str(payload.temp_limit_bottom))
        self.var_temp_ceiling.set(str(payload.temp_limit_ceiling))
        self.var_home_anim.set(str(payload.miui_home_animation))
        self.var_background_blur_supported.set(str(payload.background_blur_supported))
        self._sync_temp_enabled_state()
        self._update_recents_style_buttons()

    def restore_previous_settings(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        snap = getattr(self, "_previous_advanced_snapshot", None)
        if not isinstance(snap, dict) or not snap:
            self._log("No previous snapshot available yet.", level="error")
            return
        selection = getattr(self, "_previous_advanced_selection", None)
        if not isinstance(selection, ApplySelection):
            selection = ApplySelection(
                device_level_list=True,
                computility=True,
                advanced_visual_release=True,
                temp_limit=True,
                miui_home_animation=True,
                recents_style=False,
                background_blur_supported=True,
            )
        payload = self._payload_from_snapshot(snap)
        self._populate_inputs_from_payload(payload)
        self._run_bg("restore_previous", lambda: self._restore_previous_bg(payload, selection))

    def view_previous_settings(self) -> None:
        if self._device is None:
            self._log("No device connected. Click 'Connect Device' first.", level="error")
            return
        snap = getattr(self, "_previous_advanced_snapshot", None)
        if not isinstance(snap, dict) or not snap:
            self._log("No previous snapshot available yet.", level="error")
            return

        excluded_keys = {
            "window_animation_scale",
            "transition_animation_scale",
            "animator_duration_scale",
            "task_stack_view_layout_style",
        }

        # Only show sections that were actually applied in the last operation.
        prev_selection = getattr(self, "_previous_advanced_selection", None)
        if not isinstance(prev_selection, ApplySelection):
            prev_selection = ApplySelection(
                device_level_list=True,
                computility=True,
                advanced_visual_release=True,
                temp_limit=True,
                miui_home_animation=True,
                recents_style=False,
                background_blur_supported=True,
            )

        include_device_levels = bool(prev_selection.device_level_list)
        include_computility = bool(prev_selection.computility)
        include_advanced_visual_release = bool(prev_selection.advanced_visual_release)
        include_background_blur_supported = bool(prev_selection.background_blur_supported)
        include_miui_home_animation = bool(prev_selection.miui_home_animation)
        include_temp_limit = bool(prev_selection.temp_limit)
        
        lines = []

        # Device Level List
        if include_device_levels:
            dvl = str(snap.get("deviceLevelList", "")).strip()
            m = re.search(r"v:(\d+)\s*,\s*c:(\d+)\s*[.,]\s*g:(\d+)", dvl)
            if m:
                lines.extend(
                    [
                        "Device Level List",
                        f"v = {m.group(1)}",
                        f"c = {m.group(2)}",
                        f"g = {m.group(3)}",
                        "",
                    ]
                )
            else:
                # Fallback: show the raw combined string as-is.
                if dvl and "deviceLevelList" not in excluded_keys:
                    lines.extend(
                        ["Device Level List", f"deviceLevelList = {dvl}", ""]
                    )

        # Computility
        if include_computility:
            lines.append("Computility")
            if "cpulevel" in snap and "cpulevel" not in excluded_keys:
                lines.append(f"CPU Level = {snap.get('cpulevel')}")
            if "gpulevel" in snap and "gpulevel" not in excluded_keys:
                lines.append(f"GPU Level = {snap.get('gpulevel')}")
            lines.append("")

        # Advanced Visual Release
        if include_advanced_visual_release:
            lines.append("Advanced Visual Release")
            if (
                "advanced_visual_release" in snap
                and "advanced_visual_release" not in excluded_keys
            ):
                lines.append(
                    f"Advanced Visual Release = {snap.get('advanced_visual_release')}"
                )
            lines.append("")

        # Advanced Textures
        if include_background_blur_supported:
            lines.append("Advanced Textures")
            blur_raw = str(snap.get("background_blur_supported", "")).strip().lower()
            blur = "Enabled" if blur_raw in ("1", "true", "enabled", "on", "yes") else "Disabled"
            if (
                "background_blur_supported" in snap
                and "background_blur_supported" not in excluded_keys
            ):
                lines.append(f"Advanced Textures = {blur}")
            lines.append("")

        # Animation
        if include_miui_home_animation:
            lines.append("Animation")
            home_anim_reverse = {"0": "Relaxed", "1": "Balanced", "2": "Fast"}
            home_raw = str(snap.get("miui_home_animation_rate", "")).strip()
            home_label = home_anim_reverse.get(home_raw, home_raw or "Balanced")
            if (
                "miui_home_animation_rate" in snap
                and "miui_home_animation_rate" not in excluded_keys
            ):
                lines.append(f"Animation = {home_label}")
            lines.append("")

        # Temp Limit
        if include_temp_limit:
            lines.append("Temp Limit")
            temp_enabled = str(snap.get("rt_enable_templimit", "")).strip()
            if "rt_enable_templimit" in snap and "rt_enable_templimit" not in excluded_keys:
                lines.append(f"Enable Temp Limit = {temp_enabled}")
            if "rt_templimit_bottom" in snap and "rt_templimit_bottom" not in excluded_keys:
                lines.append(f"Bottom = {snap.get('rt_templimit_bottom')}")
            if "rt_templimit_ceiling" in snap and "rt_templimit_ceiling" not in excluded_keys:
                lines.append(f"Ceiling = {snap.get('rt_templimit_ceiling')}")

        text = "\n".join(lines)

        dialog = tk.Toplevel(self.root)
        dialog.title("View previous settings")
        dialog.geometry("400x420")
        dialog.resizable(False, False)

        txt = tk.Text(
            dialog,
            wrap="word",
            bg="#0e1116",
            fg="#e7eaf0",
            insertbackground="#e7eaf0",
            relief="flat",
            font=("Consolas", 9),
        )
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", text)
        txt.configure(state="disabled")

    def _restore_previous_bg(self, payload: SettingsPayload, selection: ApplySelection) -> None:
        assert self._device is not None
        cmds = build_shell_commands(payload, selection)
        if not cmds:
            self._log_async("Nothing to restore.", level="error")
            return
        self._log_async(f"Restoring {len(cmds)} command(s)...")
        started = time.time()
        for i, cmd in enumerate(cmds, start=1):
            self._log_async(f"[{i}/{len(cmds)}] {cmd}")
            self._device.shell(cmd)
        elapsed_ms = int((time.time() - started) * 1000)
        self._log_async(f"Restore done in {elapsed_ms} ms.", level="success")

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

    def _update_recents_style_buttons(self) -> None:
        style = getattr(self, "var_recents_style", None)
        if style is None:
            return
        current = str(style.get() or "")
        mapping = {
            "Vertically": getattr(self, "btn_recents_vertical", None),
            "Horizontally": getattr(self, "btn_recents_horizontal", None),
            "Stacked": getattr(self, "btn_recents_stacked", None),
        }
        for name, btn in mapping.items():
            if btn is None:
                continue
            try:
                if name == current:
                    btn.configure(style="success.TButton")
                else:
                    btn.configure(style="TButton")
            except Exception:
                pass

    def _toggle_animations_bg(self, disable: bool) -> None:
        assert self._device is not None
        value = "0" if disable else "1"
        cmds = [
            f"settings put global window_animation_scale {value}",
            f"settings put global transition_animation_scale {value}",
            f"settings put global animator_duration_scale {value}",
        ]
        errors: list[str] = []

        def run_one(c: str) -> None:
            try:
                self._device.shell(c)
            except Exception as e:
                errors.append(f"{c} -> {e}")

        threads: list[threading.Thread] = []
        for c in cmds:
            t = threading.Thread(target=run_one, args=(c,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        self._animations_disabled = disable
        self._ui_queue.put(("anim_btn_text", "Enable animations" if disable else "Disable animations"))

        if errors:
            self._log_async("Animation toggle completed with errors.", level="error")
        else:
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
        self._update_recents_style_buttons()
        cmd = f"settings put global task_stack_view_layout_style {style_map[style]}"
        self._run_bg("recents_style", lambda: self._run_one_quick_cmd_bg(style, cmd))

    def _run_one_quick_cmd_bg(self, label: str, cmd: str) -> None:
        assert self._device is not None
        try:
            self._device.shell(cmd)
        except Exception as e:
            self._log_async(f"Recents style '{label}' failed.", level="error")
            return
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
                    elif kind == "settings_system":
                        self._settings_full_text["system"] = msg
                        self._set_settings_table_text("system", msg)
                        self._schedule_search_settings_refresh()
                    elif kind == "settings_secure":
                        self._settings_full_text["secure"] = msg
                        self._set_settings_table_text("secure", msg)
                        self._schedule_search_settings_refresh()
                    elif kind == "settings_global":
                        self._settings_full_text["global"] = msg
                        self._set_settings_table_text("global", msg)
                        self._schedule_search_settings_refresh()
                    elif kind == "settings_props":
                        self._settings_full_text["props"] = msg
                        self._set_settings_table_text("props", msg)
                        self._schedule_search_settings_refresh()
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
                            getattr(self, "btn_restore_previous", None),
                            getattr(self, "btn_view_previous", None),
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
                    elif kind == "show_restore_previous":
                        try:
                            self.btn_restore_previous.grid(row=0, column=0, sticky="w")
                            self.btn_view_previous.grid(row=0, column=1, sticky="w", padx=(8, 0))
                        except Exception:
                            pass
                    elif kind == "anim_btn_text":
                        try:
                            self.btn_toggle_animations.configure(
                                text=msg,
                                style=("success.TButton" if "Enable" in msg else "warning.TButton"),
                            )
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
