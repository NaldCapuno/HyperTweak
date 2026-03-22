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
    lf.rowconfigure(1, weight=1)

    btns = ttk.Frame(lf)
    btns.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    btns.columnconfigure(0, weight=1)

    ttk.Button(btns, text="Refresh", command=app.refresh_current_settings).grid(
        row=0, column=0, sticky="w"
    )
    ttk.Button(btns, text="Save", command=app.save_current_settings).grid(
        row=0, column=1, sticky="e", padx=(10, 0)
    )
    ttk.Button(btns, text="Load", command=app.load_current_settings).grid(
        row=0, column=2, sticky="e", padx=(10, 0)
    )
    ttk.Button(btns, text="Apply", style="success.TButton", command=app.apply_loaded_diff).grid(
    row=0, column=3, sticky="e", padx=(10, 0)
)

    notebook = ttk.Notebook(lf)
    notebook.grid(row=1, column=0, sticky="nsew")

    def _add_settings_tab(title: str, text_attr: str) -> None:
        tab = ttk.Frame(notebook)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        txt = tk.Text(
            tab,
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

        scroll = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=scroll.set)

        setattr(app, text_attr, txt)
        notebook.add(tab, text=title)

    _add_settings_tab("system", "txt_settings_system")
    _add_settings_tab("secure", "txt_settings_secure")
    _add_settings_tab("global", "txt_settings_global")
    _add_settings_tab("props", "txt_settings_props")

    return row + 1
