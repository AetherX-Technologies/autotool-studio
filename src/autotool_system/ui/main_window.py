from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .config_panel import ConfigPanel
from .workflow_editor import WorkflowEditor


class MainWindow:
    def __init__(self, title: str = "AutoTool System") -> None:
        self._title = title
        self._root: tk.Tk | None = None
        self._views: dict[str, ttk.Frame] = {}
        self._title_var: tk.StringVar | None = None
        self._status_var: tk.StringVar | None = None
        self._recording = False

    def show(self) -> None:
        self._root = tk.Tk()
        self._root.title(self._title)
        self._root.geometry("1200x720")
        self._root.minsize(1024, 640)

        self._root.columnconfigure(1, weight=1)
        self._root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self._root, padding=10)
        sidebar.grid(row=0, column=0, sticky="ns")

        content = ttk.Frame(self._root, padding=10)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        self._title_var = tk.StringVar(value="Dashboard")
        self._status_var = tk.StringVar(value="Idle")

        header = ttk.Frame(content)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, textvariable=self._title_var, font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, textvariable=self._status_var).grid(row=0, column=1, sticky="e", padx=(10, 0))

        actions = ttk.Frame(header)
        actions.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Record", command=self._toggle_record).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Run Workflow", command=self._run_workflow).pack(side="left")

        container = ttk.Frame(content)
        container.grid(row=1, column=0, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self._views = {
            "dashboard": self._build_dashboard(container),
            "workflow": WorkflowEditor().render(container),
            "history": self._build_history(container),
            "settings": ConfigPanel().render(container),
        }

        for view in self._views.values():
            view.grid(row=0, column=0, sticky="nsew")

        for key, label in [
            ("dashboard", "Dashboard"),
            ("workflow", "Workflow Editor"),
            ("history", "Run History"),
            ("settings", "Settings"),
        ]:
            ttk.Button(sidebar, text=label, width=18, command=lambda name=key: self._show_view(name)).pack(
                pady=6, anchor="n"
            )

        self._show_view("dashboard")
        self._root.mainloop()

    def _show_view(self, name: str) -> None:
        view = self._views.get(name)
        if not view:
            return
        view.tkraise()
        if self._title_var is not None:
            self._title_var.set(
                {
                    "dashboard": "Dashboard",
                    "workflow": "Workflow Editor",
                    "history": "Run History",
                    "settings": "Settings",
                }.get(name, "AutoTool")
            )

    def _toggle_record(self) -> None:
        self._recording = not self._recording
        if self._status_var is not None:
            self._status_var.set("Recording" if self._recording else "Idle")

    def _run_workflow(self) -> None:
        if self._status_var is not None:
            self._status_var.set("Running workflow")

    def _build_dashboard(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)

        summary = ttk.LabelFrame(frame, text="Summary")
        summary.pack(fill="x", padx=12, pady=12)

        ttk.Label(summary, text="Runs today: 0").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        ttk.Label(summary, text="Success rate: --").grid(row=0, column=1, padx=8, pady=6, sticky="w")
        ttk.Label(summary, text="Active workflows: 0").grid(row=0, column=2, padx=8, pady=6, sticky="w")

        recent = ttk.LabelFrame(frame, text="Recent Runs")
        recent.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(recent, text="No runs yet.").pack(anchor="w", padx=8, pady=6)

        return frame

    def _build_history(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)
        history = ttk.LabelFrame(frame, text="Execution Logs")
        history.pack(fill="both", expand=True, padx=12, pady=12)

        text = tk.Text(history, height=10, wrap="none")
        text.insert("end", "[10:00:00] System started.\n")
        text.insert("end", "[10:00:05] No workflow executed.\n")
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, padx=8, pady=8)

        return frame
