from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

try:
    from .shared import (
        ACCENT_SECONDARY,
        ACCENT_SUCCESS,
        SUBSECTION_FG,
        SUBSECTION_BORDER,
        SUBSECTION_SCROLLBAR_BTN,
        SUBSECTION_SCROLLBAR_HOVER,
        SUBSECTION_TEXT,
        section_frame,
    )
except Exception:  # pragma: no cover
    from ui.shared import (
        ACCENT_SECONDARY,
        ACCENT_SUCCESS,
        SUBSECTION_FG,
        SUBSECTION_BORDER,
        SUBSECTION_SCROLLBAR_BTN,
        SUBSECTION_SCROLLBAR_HOVER,
        SUBSECTION_TEXT,
        section_frame,
    )

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_current_device_settings(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf = section_frame(parent, "Current Device Settings")
    lf.grid(row=row, column=0, sticky="nsew", pady=(0, 8))
    lf.columnconfigure(0, weight=1)
    lf.rowconfigure(3, weight=1)

    btns = ctk.CTkFrame(lf, fg_color="transparent")
    btns.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=12)
    btns.columnconfigure(2, weight=1)

    ctk.CTkButton(btns, text="Save", command=app.save_current_settings, width=80, fg_color=ACCENT_SECONDARY).grid(row=0, column=0, sticky="w")
    ctk.CTkButton(btns, text="Load", command=app.load_current_settings, width=80, fg_color=ACCENT_SECONDARY).grid(
        row=0, column=1, sticky="w", padx=(10, 0)
    )
    ctk.CTkButton(btns, text="Apply", command=app.apply_loaded_diff, width=88, fg_color=ACCENT_SUCCESS).grid(
        row=0, column=3, sticky="e", padx=(10, 0)
    )

    search_row = ctk.CTkFrame(lf, fg_color="transparent")
    search_row.grid(row=2, column=0, sticky="ew", pady=(0, 6), padx=12)
    search_row.columnconfigure(1, weight=1)

    ctk.CTkLabel(search_row, text="Search:").grid(row=0, column=0, sticky="w", padx=(0, 8))
    app.ent_search_settings = ctk.CTkEntry(search_row)
    app.ent_search_settings.grid(row=0, column=1, sticky="ew")
    app.ent_search_settings.bind("<KeyRelease>", app._schedule_search_settings_refresh)

    tabs = ctk.CTkTabview(lf, fg_color=SUBSECTION_FG)
    try:
        tabs.configure(border_width=1, border_color=SUBSECTION_BORDER)
    except Exception:
        pass
    tabs.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 10))
    app.nb_current_settings = tabs
    app.current_settings_tab_index = {}
    app.current_settings_wheel_exclude = []
    app.current_settings_scroll_target_by_widget = {}

    def _bind_mousewheel_to_target(widget: Any, target: Any) -> None:
        wheel_unit_multiplier = 4

        def _on_wheel(e: tk.Event) -> str:
            delta = getattr(e, "delta", 0) or 0
            if delta:
                target.yview_scroll(int(-delta / 120) * wheel_unit_multiplier, "units")
            return "break"

        def _on_linux_up(_e: tk.Event) -> str:
            target.yview_scroll(-wheel_unit_multiplier, "units")
            return "break"

        def _on_linux_down(_e: tk.Event) -> str:
            target.yview_scroll(wheel_unit_multiplier, "units")
            return "break"

        widget.bind("<MouseWheel>", _on_wheel, add="+")
        widget.bind("<Button-4>", _on_linux_up, add="+")
        widget.bind("<Button-5>", _on_linux_down, add="+")

    def _add_settings_tab(title: str, text_attr: str) -> None:
        tab = tabs.add(title)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        tab.configure(fg_color=SUBSECTION_FG)
        txt = ctk.CTkTextbox(
            tab,
            wrap="word",
            corner_radius=0,
            fg_color=SUBSECTION_FG,
            text_color=SUBSECTION_TEXT,
            border_width=0,
            scrollbar_button_color=SUBSECTION_SCROLLBAR_BTN,
            scrollbar_button_hover_color=SUBSECTION_SCROLLBAR_HOVER,
        )
        txt.grid(row=0, column=0, sticky="nsew")
        txt.configure(state="disabled")
        _bind_mousewheel_to_target(txt, txt)

        tags = list(txt.bindtags())
        if "HyperTweakSettingsText" not in tags:
            txt.bindtags(("HyperTweakSettingsText", *tags))

        setattr(app, text_attr, txt)
        app.current_settings_tab_index[title] = title
        app.current_settings_wheel_exclude.append(txt)

    _add_settings_tab("system", "txt_settings_system")
    _add_settings_tab("secure", "txt_settings_secure")
    _add_settings_tab("global", "txt_settings_global")
    _add_settings_tab("props", "txt_settings_props")

    return row + 1
