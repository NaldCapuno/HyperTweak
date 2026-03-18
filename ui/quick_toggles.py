"""Quick Toggles section for HyperTweak."""

from __future__ import annotations

from tkinter import ttk

from typing import TYPE_CHECKING

from ui.shared import section_frame

if TYPE_CHECKING:
    from main import HyperTweakApp


def build_quick_toggles(parent: ttk.Widget, app: "HyperTweakApp", row: int) -> int:
    """Build the Quick Toggles section. Returns next row."""
    lf = section_frame(parent, "Quick Toggles")
    lf.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    lf.columnconfigure(0, weight=1)
    lf.columnconfigure(1, weight=0)

    anim_box = ttk.Labelframe(lf, text="Remove animations", padding=(10, 8, 10, 10))
    anim_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    anim_box.columnconfigure(0, weight=1)

    app._animations_disabled = False
    app.btn_toggle_animations = ttk.Button(
        anim_box,
        text="Disable animations",
        style="warning.TButton",
        command=app.toggle_animations,
    )
    app.btn_toggle_animations.grid(row=0, column=0, sticky="ew")

    rec_box = ttk.Labelframe(lf, text="Recents style", padding=(10, 8, 10, 10))
    rec_box.grid(row=1, column=0, columnspan=2, sticky="ew")
    for i in range(3):
        rec_box.columnconfigure(i, weight=1)

    app.btn_recents_vertical = ttk.Button(
        rec_box, text="Vertically", command=lambda: app.set_recents_style("Vertically")
    )
    app.btn_recents_horizontal = ttk.Button(
        rec_box, text="Horizontally", command=lambda: app.set_recents_style("Horizontally")
    )
    app.btn_recents_stacked = ttk.Button(
        rec_box, text="Stacked", command=lambda: app.set_recents_style("Stacked")
    )

    app.btn_recents_vertical.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    app.btn_recents_horizontal.grid(row=0, column=1, sticky="ew", padx=(0, 6))
    app.btn_recents_stacked.grid(row=0, column=2, sticky="ew")

    return row + 1
