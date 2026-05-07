from __future__ import annotations

from typing import TYPE_CHECKING, Any

import customtkinter as ctk

try:
    from .shared import (
        add_combo,
        add_label_with_tooltip,
        add_tooltip,
        register_widget,
        section_frame_with_tooltip,
        set_section_enabled,
        titled_section,
    )
except Exception:  # pragma: no cover
    from ui.shared import (
        add_combo,
        add_label_with_tooltip,
        add_tooltip,
        register_widget,
        section_frame_with_tooltip,
        set_section_enabled,
        titled_section,
    )

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_advanced_settings(parent: Any, app: "HyperTweakApp", row: int) -> int:
    outer = section_frame_with_tooltip(
        parent,
        "Advanced Settings",
        "Restart your device for these changes to take effect.",
    )
    outer.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(1, weight=1)

    inner = ctk.CTkFrame(outer, fg_color="transparent")
    inner.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))
    inner.columnconfigure(0, weight=1)

    r = 0
    r = _section_device_levels(inner, app, r)
    r = _section_computility(inner, app, r)
    r = _section_advanced_visual_release(inner, app, r)
    r = _section_background_blur_supported(inner, app, r)
    r = _section_miui_home_animation(inner, app, r)
    r = _section_temp_limit(inner, app, r)

    return row + 1


def _section_device_levels(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf, widgets = titled_section(
        parent,
        "Device Level List",
        app.apply_device_level_list,
        app,
        tooltip_text=(
            'Adjusts the system\'s "Visual Tier" to toggle high-end effects; '
            "setting v:1, c:3, g:3 typically unlocks folder and recents blur"
        ),
    )
    lf.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 8))

    v_cb = add_combo(lf, "v", app.var_v, [1, 2, 3], 0)
    c_cb = add_combo(lf, "c", app.var_c, [1, 2, 3], 1)
    g_cb = add_combo(lf, "g", app.var_g, [1, 2, 3], 2)
    register_widget(widgets, v_cb, "normal")
    register_widget(widgets, c_cb, "normal")
    register_widget(widgets, g_cb, "normal")
    set_section_enabled(widgets, bool(app.apply_device_level_list.get()))
    return row + 1


def _section_computility(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf, widgets = titled_section(
        parent,
        "Computility",
        app.apply_computility,
        app,
        tooltip_text=(
            'Defines the performance profile for the UI engine. Higher values "trick" HyperOS into '
            "thinking you have flagship hardware, unlocking smoother physics and complex textures."
        ),
    )
    lf.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 8))

    cpu_cb = add_combo(lf, "CPU Level", app.var_cpulevel, list(range(1, 7)), 0)
    gpu_cb = add_combo(lf, "GPU Level", app.var_gpulevel, list(range(1, 7)), 1)
    register_widget(widgets, cpu_cb, "normal")
    register_widget(widgets, gpu_cb, "normal")
    set_section_enabled(widgets, bool(app.apply_computility.get()))
    return row + 1


def _section_advanced_visual_release(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf, widgets = titled_section(
        parent, "Advanced Visual Release", app.apply_advanced_visual_release, app
    )
    lf.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 8))

    avr_cb = add_combo(lf, "Advanced Visual Release", app.var_advanced_visual_release, [1, 2, 3], 0)
    register_widget(widgets, avr_cb, "normal")
    set_section_enabled(widgets, bool(app.apply_advanced_visual_release.get()))
    return row + 1


def _section_temp_limit(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf, widgets = titled_section(
        parent, "Temp Limit", app.apply_temp_limit, app, after_toggle=app._sync_temp_enabled_state
    )
    lf.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 8))

    body = ctk.CTkFrame(lf, fg_color="transparent")
    body.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 10))
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=0)

    enable_frame = ctk.CTkFrame(body, fg_color="transparent")
    enable_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    chk = ctk.CTkCheckBox(
        enable_frame,
        text="Enable Temp Limit",
        variable=app.var_temp_enable,
        command=app._sync_temp_enabled_state,
    )
    app.chk_temp_enable = chk
    chk.pack(side="left")
    lbl_enable_help = ctk.CTkLabel(enable_frame, text="?", width=20)
    lbl_enable_help.pack(side="left", padx=(6, 0))
    add_tooltip(
        lbl_enable_help,
        "When enabled, your custom Bottom and Ceiling values control thermal limits. "
        "When disabled, the phone reverts to Xiaomi's factory throttling (often starts at 40°C).",
    )
    register_widget(widgets, chk, "normal")

    temp_note = " Some devices show values x10 (e.g., 420 instead of 42); use the same scale when entering values."
    add_label_with_tooltip(
        body,
        "Bottom",
        "Temperature at which the device can stop throttling and return to full speed." + temp_note,
        1,
        pady=(0, 0),
    )
    app.ent_temp_bottom = ctk.CTkEntry(
        body,
        textvariable=app.var_temp_bottom,
        width=140,
        validate="key",
        validatecommand=app._vcmd_int,
    )
    app.ent_temp_bottom.grid(row=1, column=1, sticky="e")
    register_widget(widgets, app.ent_temp_bottom, "normal")

    add_label_with_tooltip(
        body,
        "Ceiling",
        "Maximum temperature before the system throttles the CPU and GPU to prevent damage." + temp_note,
        2,
        pady=(6, 0),
    )
    app.ent_temp_ceiling = ctk.CTkEntry(
        body,
        textvariable=app.var_temp_ceiling,
        width=140,
        validate="key",
        validatecommand=app._vcmd_int,
    )
    app.ent_temp_ceiling.grid(row=2, column=1, sticky="e", pady=(6, 0))
    register_widget(widgets, app.ent_temp_ceiling, "normal")
    set_section_enabled(widgets, bool(app.apply_temp_limit.get()))
    app._sync_temp_enabled_state()
    return row + 1


def _section_miui_home_animation(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf, widgets = titled_section(
        parent,
        "Animation",
        app.apply_miui_home_animation,
        app,
        tooltip_text="Adjusts the speed of home screen and app launch animations.",
    )
    lf.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 8))

    anim_cb = add_combo(lf, "Animation", app.var_home_anim, ["Relaxed", "Balanced", "Fast"], 0)
    register_widget(widgets, anim_cb, "normal")
    set_section_enabled(widgets, bool(app.apply_miui_home_animation.get()))
    return row + 1


def _section_background_blur_supported(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf, widgets = titled_section(
        parent,
        "Advanced Textures",
        app.apply_background_blur_supported,
        app,
        tooltip_text="Turns on system-wide blur: control centre, folder backgrounds, and recents.",
    )
    lf.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 8))

    blur_cb = add_combo(
        lf, "Advanced Textures", app.var_background_blur_supported, ["Enabled", "Disabled"], 0
    )
    register_widget(widgets, blur_cb, "normal")
    set_section_enabled(widgets, bool(app.apply_background_blur_supported.get()))
    return row + 1
