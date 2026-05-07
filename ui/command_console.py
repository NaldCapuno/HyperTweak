from __future__ import annotations

from typing import TYPE_CHECKING, Any

import customtkinter as ctk
try:
    from .shared import (
        ACCENT_SECONDARY,
        SECTION_FG,
        SUBSECTION_FG,
        SUBSECTION_BORDER,
        SUBSECTION_SCROLLBAR_BTN,
        SUBSECTION_SCROLLBAR_HOVER,
        SUBSECTION_TEXT,
    )
except Exception:  # pragma: no cover
    from ui.shared import (
        ACCENT_SECONDARY,
        SECTION_FG,
        SUBSECTION_FG,
        SUBSECTION_BORDER,
        SUBSECTION_SCROLLBAR_BTN,
        SUBSECTION_SCROLLBAR_HOVER,
        SUBSECTION_TEXT,
    )

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_command_console(parent: Any, app: "HyperTweakApp") -> ctk.CTkFrame:
    console_tab = ctk.CTkFrame(parent, fg_color=SECTION_FG)
    console_tab.rowconfigure(0, weight=1)
    console_tab.rowconfigure(1, weight=2)
    console_tab.columnconfigure(0, weight=1)

    cmd_area = ctk.CTkFrame(console_tab, fg_color="transparent")
    cmd_area.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
    cmd_area.columnconfigure(0, weight=1)
    cmd_area.rowconfigure(1, weight=1)

    console_header = ctk.CTkFrame(cmd_area, fg_color="transparent")
    console_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    console_header.columnconfigure(0, weight=1)

    ctk.CTkLabel(console_header, text="ADB shell command:").grid(row=0, column=0, sticky="w")

    cmd_row = ctk.CTkFrame(cmd_area, fg_color="transparent")
    cmd_row.grid(row=1, column=0, sticky="ew")
    cmd_row.columnconfigure(0, weight=1)
    cmd_row.rowconfigure(0, weight=1)

    app.txt_custom_cmd = ctk.CTkTextbox(
        cmd_row,
        height=90,
        corner_radius=0,
        fg_color=SUBSECTION_FG,
        text_color=SUBSECTION_TEXT,
        border_width=1,
        border_color=SUBSECTION_BORDER,
        scrollbar_button_color=SUBSECTION_SCROLLBAR_BTN,
        scrollbar_button_hover_color=SUBSECTION_SCROLLBAR_HOVER,
    )
    app.txt_custom_cmd.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

    buttons = ctk.CTkFrame(cmd_row, fg_color="transparent")
    buttons.grid(row=0, column=1, sticky="n")

    app.btn_run_custom_cmd = ctk.CTkButton(
        buttons,
        text="Run",
        width=64,
        command=app.run_custom_command,
        fg_color=ACCENT_SECONDARY,
    )
    app.btn_run_custom_cmd.grid(row=0, column=0, sticky="e")

    def _clear_command() -> None:
        app.txt_console.configure(state="normal")
        app.txt_console.delete("1.0", "end")
        app.txt_console.configure(state="disabled")

    app.btn_clear_custom_cmd = ctk.CTkButton(
        buttons,
        text="Clear",
        width=64,
        command=_clear_command,
        fg_color=ACCENT_SECONDARY,
    )
    app.btn_clear_custom_cmd.grid(row=1, column=0, sticky="e", pady=(4, 0))

    app.txt_console = ctk.CTkTextbox(
        console_tab,
        corner_radius=0,
        fg_color=SUBSECTION_FG,
        text_color=SUBSECTION_TEXT,
        border_width=1,
        border_color=SUBSECTION_BORDER,
        scrollbar_button_color=SUBSECTION_SCROLLBAR_BTN,
        scrollbar_button_hover_color=SUBSECTION_SCROLLBAR_HOVER,
    )
    app.txt_console.grid(row=1, column=0, sticky="nsew")

    return console_tab
