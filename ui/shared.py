from __future__ import annotations

import re
import tkinter as tk
from typing import TYPE_CHECKING, Any, Callable

import customtkinter as ctk

if TYPE_CHECKING:
    from main import HyperTweakApp


# Palette matched to your reference screenshot
APP_BG = ("#1F1F1F", "#1F1F1F")
SECTION_FG = ("#262626", "#262626")
SECTION_BORDER = ("#6C6C6C", "#6C6C6C")
SUBSECTION_FG = ("#2F2F2F", "#2F2F2F")
SUBSECTION_BORDER = ("#7A7A7A", "#7A7A7A")
SUBSECTION_TEXT = ("#EDEDED", "#EDEDED")
SUBSECTION_SCROLLBAR_BTN = ("#6C6C6C", "#6C6C6C")
SUBSECTION_SCROLLBAR_HOVER = ("#7A7A7A", "#7A7A7A")

# Button accents from the screenshot
ACCENT_PRIMARY = ("#2F5F85", "#2F5F85")        # blue-gray (global header buttons)
ACCENT_SECONDARY = ("#355F82", "#355F82")      # slightly muted blue-gray (panel buttons)
ACCENT_SUCCESS = ("#00C08A", "#00C08A")        # teal-green (Apply)
ACCENT_DANGER = ("#E74C3C", "#E74C3C")         # red (Reboot)
ACCENT_WARNING = ("#C57C00", "#C57C00")        # optional orange (not prominent in ref)

# Global actions (top/bottom bars) – keep slightly more punch than panel buttons
ACCENT_GLOBAL_PRIMARY = ("#2F5F85", "#2F5F85")
ACCENT_GLOBAL_SUCCESS = ("#00C08A", "#00C08A")
ACCENT_GLOBAL_DANGER = ("#E74C3C", "#E74C3C")


class SimpleToolTip:
    def __init__(self, widget: Any, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tipwindow: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event: object = None) -> None:
        if self.tipwindow is not None:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + 24
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#1f2329",
            foreground="#e7eaf0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=4,
            font=("Segoe UI", 9),
        )
        lbl.pack()
        self.tipwindow = tw

    def _hide(self, _event: object = None) -> None:
        if self.tipwindow is not None:
            self.tipwindow.destroy()
            self.tipwindow = None


def section_frame(parent: Any, title: str) -> ctk.CTkFrame:
    lf = ctk.CTkFrame(
        parent,
        corner_radius=8,
        fg_color=SECTION_FG,
        border_width=1,
        border_color=SECTION_BORDER,
    )
    lf.columnconfigure(0, weight=1)
    title_lbl = ctk.CTkLabel(lf, text=title, font=("Segoe UI", 16, "bold"))
    title_lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 6))
    return lf


def section_frame_with_tooltip(parent: Any, title: str, tooltip_text: str) -> ctk.CTkFrame:
    lf = ctk.CTkFrame(
        parent,
        corner_radius=8,
        fg_color=SECTION_FG,
        border_width=1,
        border_color=SECTION_BORDER,
    )
    lf.columnconfigure(0, weight=1)
    label_row = ctk.CTkFrame(lf, fg_color="transparent")
    label_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 6))
    label_row.columnconfigure(0, weight=1)
    ctk.CTkLabel(label_row, text=title, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
    lbl_help = ctk.CTkLabel(label_row, text="?", width=20)
    lbl_help.grid(row=0, column=1, sticky="e")
    add_tooltip(lbl_help, tooltip_text)
    return lf


def add_tooltip(widget: Any, text: str) -> None:
    SimpleToolTip(widget, text)


def add_label_with_tooltip(parent: Any, label_text: str, tooltip_text: str, row: int, pady: tuple[int, int] = (0, 0)) -> None:
    label_frame = ctk.CTkFrame(parent, fg_color="transparent")
    label_frame.grid(row=row, column=0, sticky="w", pady=pady, padx=(0, 10))
    ctk.CTkLabel(label_frame, text=label_text).pack(side="left")
    lbl_help = ctk.CTkLabel(label_frame, text="?", width=20)
    lbl_help.pack(side="left", padx=(6, 0))
    add_tooltip(lbl_help, tooltip_text)


def labelframe_with_tooltip_icon(
    parent: Any, title: str, tooltip_text: str, padding: tuple[int, int, int, int] = (10, 8, 10, 10)
) -> ctk.CTkFrame:
    lf = ctk.CTkFrame(
        parent,
        corner_radius=8,
        fg_color=SUBSECTION_FG,
        border_width=1,
        border_color=SUBSECTION_BORDER,
    )
    lf.columnconfigure(0, weight=1)
    label_row = ctk.CTkFrame(lf, fg_color="transparent")
    label_row.grid(row=0, column=0, sticky="ew", padx=(padding[0], padding[2]), pady=(padding[1], 6))
    label_row.columnconfigure(0, weight=1)
    # Small inner padding prevents text clipping against rounded borders.
    ctk.CTkLabel(label_row, text=title, font=("Segoe UI", 14, "bold"), anchor="w").grid(
        row=0, column=0, sticky="ew", padx=(2, 0)
    )
    lbl_help = ctk.CTkLabel(label_row, text="?", width=20)
    lbl_help.grid(row=0, column=1, sticky="e")
    add_tooltip(lbl_help, tooltip_text)
    return lf


def titled_section(
    parent: Any,
    title: str,
    enabled_var: tk.BooleanVar,
    app: HyperTweakApp,
    after_toggle: Callable[[], None] | None = None,
    tooltip_text: str | None = None,
) -> tuple[ctk.CTkFrame, list[tuple[Any, str]]]:
    lf = ctk.CTkFrame(
        parent,
        corner_radius=8,
        fg_color=SUBSECTION_FG,
        border_width=1,
        border_color=SUBSECTION_BORDER,
    )
    lf.grid_columnconfigure(2, weight=1)

    label = ctk.CTkFrame(lf, fg_color="transparent")
    label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8, 6))
    chk = ctk.CTkCheckBox(label, variable=enabled_var, text="", width=24)
    chk.pack(side="left", padx=(0, 6))
    ctk.CTkLabel(label, text=title, font=("Segoe UI", 14, "bold")).pack(side="left")
    if tooltip_text:
        lbl_help = ctk.CTkLabel(label, text="?", width=20)
        lbl_help.pack(side="right", padx=(6, 0))
        add_tooltip(lbl_help, tooltip_text)

    widgets: list[tuple[Any, str]] = []

    def on_toggle() -> None:
        set_section_enabled(widgets, bool(enabled_var.get()))
        if after_toggle is not None:
            after_toggle()

    chk.configure(command=on_toggle)
    return lf, widgets


def register_widget(widgets: list[tuple[Any, str]], widget: Any, enabled_state: str) -> None:
    widgets.append((widget, enabled_state))


def set_section_enabled(widgets: list[tuple[Any, str]], enabled: bool) -> None:
    for w, _enabled_state in widgets:
        try:
            w.configure(state=("normal" if enabled else "disabled"))
        except tk.TclError:
            pass


def add_combo(
    parent: Any,
    label: str,
    var: tk.Variable,
    values: list[Any],
    r: int,
    tooltip_text: str | None = None,
) -> ctk.CTkOptionMenu:
    # Keep a bottom inset so each section card has visible breathing room.
    pady = (0 if r == 0 else 6, 8)
    padx = (12, 10)
    if tooltip_text:
        label_frame = ctk.CTkFrame(parent, fg_color="transparent")
        label_frame.grid(row=r + 1, column=0, sticky="w", pady=pady, padx=padx)
        ctk.CTkLabel(label_frame, text=label).pack(side="left")
        lbl_help = ctk.CTkLabel(label_frame, text="?", width=20)
        lbl_help.pack(side="left", padx=(6, 0))
        add_tooltip(lbl_help, tooltip_text)
    else:
        ctk.CTkLabel(parent, text=label).grid(
            row=r + 1, column=0, sticky="w", pady=pady, padx=padx
        )

    menu = ctk.CTkOptionMenu(parent, values=[str(v) for v in values], variable=var, width=140)
    menu.grid(row=r + 1, column=2, sticky="e", pady=pady, padx=(0, 12))
    return menu


def apply_current_kv(app: HyperTweakApp, kv: str) -> None:
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
        updater = getattr(app, "_update_recents_style_buttons", None)
        if callable(updater):
            updater()
    elif key == "background_blur_supported":
        vlow = val.lower()
        if vlow in ("1", "true", "enabled"):
            app.var_background_blur_supported.set("Enabled")
        elif vlow in ("0", "false", "disabled"):
            app.var_background_blur_supported.set("Disabled")
