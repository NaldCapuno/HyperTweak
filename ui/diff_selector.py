import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.widgets.scrolled import ScrolledFrame

class DiffSelectionWindow(tb.Toplevel):
    def __init__(self, parent, diff_list, on_apply_callback):
        super().__init__(title="Select Settings to Apply", size=(650, 500), resizable=(False, False))
        self.on_apply_callback = on_apply_callback
        self.vars = []

        lbl = ttk.Label(self, text="Select the changes you want to apply to your device:", padding=10)
        lbl.pack(fill="x")

        self.scroll = ScrolledFrame(self, autohide=True, padding=10)
        self.scroll.pack(fill="both", expand=True)

        header = ttk.Frame(self.scroll)
        header.pack(fill="x", pady=(0, 5))
        ttk.Label(header, text="Setting", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(header, text="From (Device) -> To (File)", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=5)
        header.columnconfigure(1, weight=1)

        for i, item in enumerate(diff_list):
            var = tk.BooleanVar(value=True)
            self.vars.append((var, item))

            row = ttk.Frame(self.scroll)
            row.pack(fill="x", pady=2)
            
            chk = ttk.Checkbutton(row, variable=var)
            chk.grid(row=0, column=0, padx=5)
            
            name_lbl = ttk.Label(row, text=f"[{item[0]}] {item[1]}", foreground="#9aa4b2")
            name_lbl.grid(row=0, column=1, sticky="w")
            
            val_text = f"'{item[2]}' → '{item[3]}'"
            val_lbl = ttk.Label(row, text=val_text)
            val_lbl.grid(row=0, column=2, sticky="w", padx=10)
            
            row.columnconfigure(1, weight=1)

        footer = ttk.Frame(self, padding=10)
        footer.pack(fill="x")
        
        ttk.Button(footer, text="Apply Selected", style="success.TButton", command=self._on_apply).pack(side="right", padx=5)
        ttk.Button(footer, text="Cancel", style="secondary.TButton", command=self.destroy).pack(side="right")

    def _on_apply(self):
        selected_items = [item for var, item in self.vars if var.get()]
        if selected_items:
            self.on_apply_callback(selected_items)
        self.destroy()