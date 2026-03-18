"""Command Console tab for HyperTweak."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_command_console(parent: ttk.Widget, app: "HyperTweakApp") -> ttk.Frame:
    """Build the Command Console tab. Returns the console_tab frame."""
    console_tab = ttk.Frame(parent)
    console_tab.rowconfigure(0, weight=1)
    console_tab.rowconfigure(1, weight=2)
    console_tab.columnconfigure(0, weight=1)

    cmd_area = ttk.Frame(console_tab)
    cmd_area.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
    cmd_area.columnconfigure(0, weight=1)
    cmd_area.rowconfigure(1, weight=1)

    console_header = ttk.Frame(cmd_area)
    console_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    console_header.columnconfigure(0, weight=1)

    ttk.Label(console_header, text="ADB shell command:").grid(row=0, column=0, sticky="w")

    cmd_row = ttk.Frame(cmd_area)
    cmd_row.grid(row=1, column=0, sticky="ew")
    cmd_row.columnconfigure(0, weight=1)

    app.txt_custom_cmd = tk.Text(
        cmd_row,
        height=3,
        wrap="char",
        padx=6,
        pady=4,
        bg="#0e1116",
        fg="#e7eaf0",
        insertbackground="#e7eaf0",
        relief="flat",
    )
    app.txt_custom_cmd.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    app.txt_custom_cmd.insert("1.0", "getprop ro.product.model")

    app.btn_run_custom_cmd = ttk.Button(
        cmd_row,
        text="Run",
        width=8,
        command=app.run_custom_command,
    )
    app.btn_run_custom_cmd.grid(row=0, column=1, sticky="e")

    app.txt_console = tk.Text(
        console_tab,
        wrap="word",
        padx=10,
        pady=6,
        bg="#0e1116",
        fg="#e7eaf0",
        insertbackground="#e7eaf0",
        relief="flat",
    )
    app.txt_console.grid(row=1, column=0, sticky="nsew")

    return console_tab
