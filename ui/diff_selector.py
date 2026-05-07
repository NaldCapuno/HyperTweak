import tkinter as tk

import customtkinter as ctk


class DiffSelectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, diff_list, on_apply_callback):
        super().__init__(parent)
        self.title("Select Settings to Apply")
        self.geometry("650x500")
        self.resizable(False, False)
        self.on_apply_callback = on_apply_callback
        self.vars = []

        lbl = ctk.CTkLabel(self, text="Select the changes you want to apply to your device:")
        lbl.pack(fill="x", padx=10, pady=10)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header, text="Setting", font=("Segoe UI", 12, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        ctk.CTkLabel(header, text="From (Device) -> To (File)", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=2, sticky="w", padx=5
        )
        header.columnconfigure(1, weight=1)

        for item in diff_list:
            var = tk.BooleanVar(value=True)
            self.vars.append((var, item))

            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)

            chk = ctk.CTkCheckBox(row, text="", variable=var, width=24)
            chk.grid(row=0, column=0, padx=5)

            name_lbl = ctk.CTkLabel(row, text=f"[{item[0]}] {item[1]}")
            name_lbl.grid(row=0, column=1, sticky="w")

            val_text = f"'{item[2]}' -> '{item[3]}'"
            val_lbl = ctk.CTkLabel(row, text=val_text)
            val_lbl.grid(row=0, column=2, sticky="w", padx=10)

            row.columnconfigure(1, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(footer, text="Apply Selected", command=self._on_apply, width=120).pack(side="right", padx=5)
        ctk.CTkButton(footer, text="Cancel", command=self.destroy, width=90).pack(side="right")

    def _on_apply(self):
        selected_items = [item for var, item in self.vars if var.get()]
        if selected_items:
            self.on_apply_callback(selected_items)
        self.destroy()
