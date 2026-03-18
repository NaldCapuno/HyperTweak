"""Current Device Settings section for HyperTweak."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ttkbootstrap.widgets.scrolled import ScrolledFrame

from typing import TYPE_CHECKING

from ui.shared import section_frame

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_current_device_settings(parent: ttk.Widget, app: "HyperTweakApp", row: int) -> int:
    """Build the Current Device Settings section. Returns next row."""
    lf = section_frame(parent, "Current Device Settings")
    lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    lf.columnconfigure(1, weight=1)

    btns = ttk.Frame(lf)
    btns.grid(row=0, column=0, sticky="w", columnspan=2, pady=(0, 8))

    ttk.Button(btns, text="Refresh from Device", command=app.refresh_current_settings).grid(
        row=0, column=0, sticky="w"
    )
    ttk.Button(btns, text="Save", command=app.save_current_settings).grid(
        row=0, column=1, sticky="w", padx=(10, 0)
    )
    ttk.Button(btns, text="Load", command=app.load_current_settings).grid(
        row=0, column=2, sticky="w", padx=(10, 0)
    )

    values = ScrolledFrame(lf, autohide=False, height=170, padding=(0, 0, 0, 0))
    values.grid(row=1, column=0, columnspan=2, sticky="ew")
    values.columnconfigure(0, weight=1)

    rows = ttk.Frame(values)
    rows.grid(row=0, column=0, sticky="ew")
    rows.columnconfigure(1, weight=1)

    def add(r: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(rows, text=label).grid(row=r, column=0, sticky="w", padx=(0, 10))
        ttk.Label(rows, textvariable=var, foreground="#c9d1d9").grid(row=r, column=1, sticky="w")

    r = 0
    add(r, "window_animation_scale", app.cur_window_animation_scale); r += 1
    add(r, "transition_animation_scale", app.cur_transition_animation_scale); r += 1
    add(r, "animator_duration_scale", app.cur_animator_duration_scale); r += 1
    add(r, "task_stack_view_layout_style", app.cur_recents_style); r += 1
    add(r, "deviceLevelList", app.cur_device_level_list); r += 1
    add(r, "cpulevel", app.cur_cpulevel); r += 1
    add(r, "gpulevel", app.cur_gpulevel); r += 1
    add(r, "advanced_visual_release", app.cur_advanced_visual_release); r += 1
    add(r, "background_blur_supported", app.cur_background_blur_supported); r += 1
    add(r, "miui_home_animation_rate", app.cur_miui_home_animation_rate); r += 1
    add(r, "rt_enable_templimit", app.cur_temp_limit_enabled); r += 1
    add(r, "rt_templimit_bottom", app.cur_temp_limit_bottom); r += 1
    add(r, "rt_templimit_ceiling", app.cur_temp_limit_ceiling); r += 1

    return row + 1
