from __future__ import annotations

from typing import TYPE_CHECKING, Any

import customtkinter as ctk

try:
    from .shared import (
        ACCENT_PRIMARY,
        ACCENT_SECONDARY,
        ACCENT_WARNING,
        SUBSECTION_BORDER,
        labelframe_with_tooltip_icon,
        section_frame_with_tooltip,
    )
except Exception:  # pragma: no cover
    from ui.shared import (
        ACCENT_PRIMARY,
        ACCENT_SECONDARY,
        ACCENT_WARNING,
        SUBSECTION_BORDER,
        labelframe_with_tooltip_icon,
        section_frame_with_tooltip,
    )

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_quick_toggles(parent: Any, app: "HyperTweakApp", row: int) -> int:
    lf = section_frame_with_tooltip(
        parent,
        "Quick Toggles",
        "Applies settings instantly without restarting the device.",
    )
    lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    lf.columnconfigure(0, weight=1)
    lf.columnconfigure(1, weight=0)

    anim_box = labelframe_with_tooltip_icon(
        lf,
        "Remove animations",
        "Reduces some animations. Control centre and recents animations remain.",
    )
    anim_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8), padx=12)
    anim_box.columnconfigure(0, weight=1)

    app._animations_disabled = False
    app.btn_toggle_animations = ctk.CTkButton(
        anim_box,
        text="Disable animations",
        command=app.toggle_animations,
        fg_color=ACCENT_WARNING,
    )
    app.btn_toggle_animations.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

    rec_box = labelframe_with_tooltip_icon(
        lf,
        "Recents style",
        "Changes the style of the recents view. Stacked layout requires the latest system launcher version.",
    )
    rec_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
    rec_box.columnconfigure(0, weight=1)

    btn_row = ctk.CTkFrame(rec_box, fg_color="transparent")
    btn_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
    for i in range(3):
        btn_row.columnconfigure(i, weight=1)

    # Default buttons are neutral; selected state is applied by app._update_recents_style_buttons().
    neutral = ACCENT_SECONDARY
    neutral_hover = ("#49739A", "#49739A")
    app.btn_recents_vertical = ctk.CTkButton(
        rec_box,
        text="Vertically",
        command=lambda: app.set_recents_style("Vertically"),
        fg_color=neutral,
        hover_color=neutral_hover,
        border_width=0,
    )
    app.btn_recents_horizontal = ctk.CTkButton(
        rec_box,
        text="Horizontally",
        command=lambda: app.set_recents_style("Horizontally"),
        fg_color=neutral,
        hover_color=neutral_hover,
        border_width=0,
    )
    app.btn_recents_stacked = ctk.CTkButton(
        rec_box,
        text="Stacked",
        command=lambda: app.set_recents_style("Stacked"),
        fg_color=neutral,
        hover_color=neutral_hover,
        border_width=0,
    )

    app.btn_recents_vertical.grid(in_=btn_row, row=0, column=0, sticky="ew", padx=(0, 6))
    app.btn_recents_horizontal.grid(in_=btn_row, row=0, column=1, sticky="ew", padx=(0, 6))
    app.btn_recents_stacked.grid(in_=btn_row, row=0, column=2, sticky="ew")

    # Ensure the default selection is visually highlighted.
    try:
        app._update_recents_style_buttons()
    except Exception:
        pass

    return row + 1
