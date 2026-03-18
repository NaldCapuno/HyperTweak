"""Shared UI helpers for HyperTweak sections."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from main import HyperTweakApp


def section_frame(parent: ttk.Widget, title: str) -> ttk.Labelframe:
    """Create a simple labelframe with title."""
    lf = ttk.Labelframe(parent, text=title, padding=(12, 10, 12, 10))
    lf.columnconfigure(1, weight=1)
    return lf


def titled_section(
    parent: ttk.Widget,
    title: str,
    enabled_var: tk.BooleanVar,
    app: HyperTweakApp,
    after_toggle: Callable[[], None] | None = None,
) -> tuple[ttk.Labelframe, list[tuple[ttk.Widget, str]]]:
    """Create a labelframe with checkbox and title; returns (frame, widgets list)."""
    lf = ttk.Labelframe(parent, padding=(12, 10, 12, 10))
    lf.grid_columnconfigure(1, weight=1)

    label = ttk.Frame(lf)
    chk = ttk.Checkbutton(label, variable=enabled_var, text="")
    chk.pack(side="left", padx=(0, 6))
    ttk.Label(label, text=title, font=("Segoe UI", 10, "bold")).pack(side="left")
    lf.configure(labelwidget=label)

    widgets: list[tuple[ttk.Widget, str]] = []

    def on_toggle() -> None:
        set_section_enabled(widgets, bool(enabled_var.get()))
        if after_toggle is not None:
            after_toggle()

    chk.configure(command=on_toggle)
    return lf, widgets


def register_widget(
    widgets: list[tuple[ttk.Widget, str]], widget: ttk.Widget, enabled_state: str
) -> None:
    """Register a widget for enable/disable toggling."""
    widgets.append((widget, enabled_state))


def set_section_enabled(widgets: list[tuple[ttk.Widget, str]], enabled: bool) -> None:
    """Enable or disable all registered widgets in a section."""
    for w, enabled_state in widgets:
        try:
            w.configure(state=(enabled_state if enabled else "disabled"))
        except tk.TclError:
            pass


def add_combo(
    parent: ttk.Widget,
    label: str,
    var: tk.Variable,
    values: list[Any],
    r: int,
) -> ttk.Combobox:
    """Add a label + combobox row to parent."""
    ttk.Label(parent, text=label).grid(
        row=r, column=0, sticky="w", pady=(0 if r == 0 else 6, 0), padx=(0, 10)
    )
    cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=18)
    cb.configure(bootstyle="secondary")
    cb.grid(row=r, column=2, sticky="e", pady=(0 if r == 0 else 6, 0))
    return cb


def apply_current_kv(app: HyperTweakApp, kv: str) -> None:
    """Apply a key=value from device refresh to app state."""
    if "=" not in kv:
        return
    key, val = kv.split("=", 1)
    key = key.strip()
    val = val.strip()

    if key == "deviceLevelList":
        app.cur_device_level_list.set(val)
        m = re.search(r"v:(\d+)\s*,\s*c:(\d+)\s*[.,]\s*g:(\d+)", val)
        if m:
            try:
                app.var_v.set(int(m.group(1)))
                app.var_c.set(int(m.group(2)))
                app.var_g.set(int(m.group(3)))
            except Exception:
                pass
        return

    mapping: dict[str, tk.StringVar] = {
        "window_animation_scale": app.cur_window_animation_scale,
        "transition_animation_scale": app.cur_transition_animation_scale,
        "animator_duration_scale": app.cur_animator_duration_scale,
        "cpulevel": app.cur_cpulevel,
        "gpulevel": app.cur_gpulevel,
        "advanced_visual_release": app.cur_advanced_visual_release,
        "rt_enable_templimit": app.cur_temp_limit_enabled,
        "rt_templimit_bottom": app.cur_temp_limit_bottom,
        "rt_templimit_ceiling": app.cur_temp_limit_ceiling,
        "miui_home_animation_rate": app.cur_miui_home_animation_rate,
        "task_stack_view_layout_style": app.cur_recents_style,
        "background_blur_supported": app.cur_background_blur_supported,
    }
    if key in mapping:
        mapping[key].set(val)

    if key == "cpulevel" and val.isdigit():
        app.var_cpulevel.set(int(val))
    elif key == "gpulevel" and val.isdigit():
        app.var_gpulevel.set(int(val))
    elif key == "advanced_visual_release" and val.isdigit():
        app.var_advanced_visual_release.set(int(val))
    elif key == "rt_enable_templimit":
        app.var_temp_enable.set(val in ("1", "true", "True", "enabled", "on", "ON"))
        app._sync_temp_enabled_state()
    elif key == "rt_templimit_bottom" and val.isdigit():
        app.var_temp_bottom.set(val)
    elif key == "rt_templimit_ceiling" and val.isdigit():
        app.var_temp_ceiling.set(val)
    elif key == "miui_home_animation_rate":
        home_anim_reverse = {"0": "Relaxed", "1": "Balanced", "2": "Fast"}
        if val in home_anim_reverse:
            app.var_home_anim.set(home_anim_reverse[val])
        elif val in ("Relaxed", "Balanced", "Fast"):
            app.var_home_anim.set(val)
    elif key == "task_stack_view_layout_style":
        recents_style_reverse = {"0": "Vertically", "1": "Horizontally", "2": "Stacked"}
        if val in recents_style_reverse:
            app.var_recents_style.set(recents_style_reverse[val])
        elif val in ("Vertically", "Horizontally", "Stacked"):
            app.var_recents_style.set(val)
    elif key == "background_blur_supported":
        vlow = val.lower()
        if vlow in ("1", "true", "enabled"):
            app.var_background_blur_supported.set("Enabled")
        elif vlow in ("0", "false", "disabled"):
            app.var_background_blur_supported.set("Disabled")
