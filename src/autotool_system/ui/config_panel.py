from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ConfigPanel:
    def render(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)

        section = ttk.LabelFrame(frame, text="System Settings")
        section.pack(fill="x", padx=12, pady=12)

        ttk.Label(section, text="Default download path").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(section, width=40).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(section, text="Emergency stop hotkey").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(section, width=20).grid(row=1, column=1, sticky="w", padx=8, pady=6)

        autostart = tk.BooleanVar(value=True)
        ttk.Checkbutton(section, text="Start on boot", variable=autostart).grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )

        section.columnconfigure(1, weight=1)
        return frame
