from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from typing import TYPE_CHECKING

from ui.shared import section_frame

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_current_device_settings(parent: ttk.Widget, app: "HyperTweakApp", row: int) -> int:
    lf = section_frame(parent, "Current Device Settings")
    lf.grid(row=row, column=0, sticky="nsew", pady=(0, 8))
    lf.columnconfigure(0, weight=1)
    lf.rowconfigure(2, weight=1)

    btns = ttk.Frame(lf)
    btns.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    btns.columnconfigure(2, weight=1)

    ttk.Button(btns, text="Save", command=app.save_current_settings).grid(
        row=0, column=0, sticky="w"
    )
    ttk.Button(btns, text="Load", command=app.load_current_settings).grid(
        row=0, column=1, sticky="w", padx=(10, 0)
    )
    ttk.Button(btns, text="Apply", style="success.TButton", command=app.apply_loaded_diff).grid(
        row=0, column=3, sticky="e", padx=(10, 0)
    )

    search_row = ttk.Frame(lf)
    search_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
    search_row.columnconfigure(1, weight=1)

    ttk.Label(search_row, text="Search:").grid(row=0, column=0, sticky="w", padx=(0, 8))
    app.ent_search_settings = ttk.Entry(search_row)
    app.ent_search_settings.grid(row=0, column=1, sticky="ew")
    app.ent_search_settings.bind("<KeyRelease>", app._schedule_search_settings_refresh)

    notebook = ttk.Notebook(lf)
    notebook.grid(row=2, column=0, sticky="nsew")
    app.nb_current_settings = notebook
    app.current_settings_tab_index = {}
    app.current_settings_wheel_exclude = []
    app.current_settings_scroll_target_by_widget = {}

    def _bind_mousewheel_to_target(widget: tk.Widget, target: tk.Text) -> None:
        wheel_unit_multiplier = 3

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

        widget.bind("<MouseWheel>", _on_wheel)
        widget.bind("<Button-4>", _on_linux_up)
        widget.bind("<Button-5>", _on_linux_down)

    def _add_settings_tab(title: str, text_attr: str) -> None:
        tab = ttk.Frame(notebook)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        txt = tk.Text(
            tab,
            height=18,
            wrap="word",
            padx=8,
            pady=4,
            bg="#0e1116",
            fg="#e7eaf0",
            insertbackground="#e7eaf0",
            relief="flat",
        )
        txt.grid(row=0, column=0, sticky="nsew")
        txt.configure(state="disabled")
        _bind_mousewheel_to_target(txt, txt)
        
        tags = list(txt.bindtags())
        if "HyperTweakSettingsText" not in tags:
            txt.bindtags(("HyperTweakSettingsText", *tags))

        scroll = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=scroll.set)
        _bind_mousewheel_to_target(scroll, txt)
        stags = list(scroll.bindtags())
        if "HyperTweakSettingsScrollbar" not in stags:
            scroll.bindtags(("HyperTweakSettingsScrollbar", *stags))
        app.current_settings_scroll_target_by_widget[str(scroll)] = txt

        setattr(app, text_attr, txt)
        notebook.add(tab, text=title)
        app.current_settings_tab_index[title] = notebook.index("end") - 1
        app.current_settings_wheel_exclude.append(txt)
        app.current_settings_wheel_exclude.append(scroll)

    _add_settings_tab("system", "txt_settings_system")
    _add_settings_tab("secure", "txt_settings_secure")
    _add_settings_tab("global", "txt_settings_global")
    _add_settings_tab("props", "txt_settings_props")

    return row + 1
