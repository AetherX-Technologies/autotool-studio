from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from ..core.workflow_builder import WorkflowBuilder
from ..utils.flowgram_io import FlowGramError, graph_counts, normalize_flowgram_payload
from .flowgram_launcher import FlowGramLauncher


class WorkflowEditor:
    def __init__(self) -> None:
        self._launcher = FlowGramLauncher()
        self._workflow = self._empty_workflow()
        self._graph_path: Path | None = None

        self._workflow_id_var: tk.StringVar | None = None
        self._workflow_name_var: tk.StringVar | None = None
        self._graph_path_var: tk.StringVar | None = None
        self._summary_var: tk.StringVar | None = None
        self._status_var: tk.StringVar | None = None

        self._node_list: tk.Listbox | None = None
        self._error_text: tk.Text | None = None

    def render(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        self._workflow_id_var = tk.StringVar(value=self._workflow["id"])
        self._workflow_name_var = tk.StringVar(value=self._workflow["name"])
        self._graph_path_var = tk.StringVar(value="No FlowGram file loaded")
        self._summary_var = tk.StringVar(value="Nodes: 0 | Edges: 0")
        self._status_var = tk.StringVar(value="Idle")

        palette = ttk.LabelFrame(frame, text="FlowGram Controls")
        palette.grid(row=0, column=0, sticky="ns", padx=12, pady=12)

        ttk.Label(palette, text="FlowGram (GitHub) integration").pack(anchor="w", padx=8, pady=(8, 4))
        ttk.Button(palette, text="Start FlowGram Demo", command=self._start_flowgram_demo).pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Button(palette, text="Load FlowGram JSON", command=self._load_flowgram_json).pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Button(palette, text="Export FlowGram JSON", command=self._export_flowgram_json).pack(
            anchor="w", padx=8, pady=4
        )

        ttk.Label(palette, text="FlowGram file").pack(anchor="w", padx=8, pady=(12, 2))
        ttk.Label(palette, textvariable=self._graph_path_var, wraplength=200).pack(
            anchor="w", padx=8, pady=(0, 8)
        )

        canvas = ttk.LabelFrame(frame, text="FlowGram Graph")
        canvas.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        canvas.columnconfigure(0, weight=1)
        canvas.rowconfigure(1, weight=1)

        ttk.Label(canvas, textvariable=self._summary_var).grid(row=0, column=0, sticky="w", padx=8, pady=8)

        list_frame = ttk.Frame(canvas)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._node_list = tk.Listbox(list_frame, height=12, yscrollcommand=scrollbar.set)
        self._node_list.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self._node_list.yview)

        properties = ttk.LabelFrame(frame, text="Workflow Metadata")
        properties.grid(row=0, column=2, sticky="nsew", padx=12, pady=12)
        properties.columnconfigure(0, weight=1)
        properties.rowconfigure(6, weight=1)

        ttk.Label(properties, text="Workflow ID").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(properties, textvariable=self._workflow_id_var).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(0, 8)
        )
        ttk.Label(properties, text="Workflow name").grid(row=2, column=0, sticky="w", padx=8, pady=(0, 2))
        ttk.Entry(properties, textvariable=self._workflow_name_var).grid(
            row=3, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        action_row = ttk.Frame(properties)
        action_row.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(action_row, text="Validate", command=self._validate_workflow).pack(side="left")
        ttk.Button(action_row, text="Save Workflow", command=self._save_workflow).pack(side="left", padx=6)

        ttk.Label(properties, text="Validation results").grid(row=5, column=0, sticky="w", padx=8, pady=(0, 2))
        self._error_text = tk.Text(properties, height=8, wrap="word")
        self._error_text.grid(row=6, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._error_text.tag_configure("error", foreground="#b00020")
        self._error_text.tag_configure("ok", foreground="#1b5e20")
        self._error_text.configure(state="disabled")

        ttk.Label(properties, textvariable=self._status_var, wraplength=220).grid(
            row=7, column=0, sticky="w", padx=8, pady=(0, 8)
        )

        self._refresh_graph_view()
        return frame

    def _empty_workflow(self) -> dict[str, object]:
        return {"id": "", "name": "", "graph": {"nodes": [], "edges": []}}

    def _sync_metadata(self) -> None:
        if self._workflow_id_var is not None:
            self._workflow["id"] = self._workflow_id_var.get().strip()
        if self._workflow_name_var is not None:
            self._workflow["name"] = self._workflow_name_var.get().strip()

    def _start_flowgram_demo(self) -> None:
        message = self._launcher.start_demo()
        self._set_status(message)

    def _load_flowgram_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Load FlowGram JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            workflow = normalize_flowgram_payload(payload)
        except (OSError, json.JSONDecodeError, FlowGramError) as exc:
            self._set_status(f"Load failed: {exc}")
            self._show_errors([str(exc)])
            return

        if not workflow["id"]:
            workflow["id"] = self._workflow.get("id", "")
        if not workflow["name"]:
            workflow["name"] = self._workflow.get("name", "")

        self._workflow = workflow
        self._graph_path = Path(path)
        if self._graph_path_var is not None:
            self._graph_path_var.set(str(self._graph_path))
        if self._workflow_id_var is not None:
            self._workflow_id_var.set(self._workflow.get("id", ""))
        if self._workflow_name_var is not None:
            self._workflow_name_var.set(self._workflow.get("name", ""))

        self._refresh_graph_view()
        self._show_errors([])
        self._set_status("FlowGram JSON loaded.")

    def _export_flowgram_json(self) -> None:
        graph = self._workflow.get("graph", {"nodes": [], "edges": []})
        path = filedialog.asksaveasfilename(
            title="Export FlowGram JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(graph, handle, indent=2, ensure_ascii=True)
        except OSError as exc:
            self._set_status(f"Export failed: {exc}")
            return

        self._graph_path = Path(path)
        if self._graph_path_var is not None:
            self._graph_path_var.set(str(self._graph_path))
        self._set_status("FlowGram JSON exported.")

    def _validate_workflow(self) -> None:
        self._sync_metadata()
        builder = WorkflowBuilder()
        errors = builder.validate(self._workflow)
        self._show_errors(errors)
        if errors:
            self._set_status(f"Validation errors: {len(errors)}")
        else:
            self._set_status("Validation passed.")

    def _save_workflow(self) -> None:
        self._sync_metadata()
        builder = WorkflowBuilder()
        errors = builder.validate(self._workflow)
        if errors:
            self._show_errors(errors)
            self._set_status("Fix validation errors before saving.")
            return

        workflow_id = self._workflow.get("id") or "workflow"
        target_dir = Path("data") / "workflows"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save Workflow",
            initialdir=str(target_dir),
            initialfile=f"{workflow_id}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self._workflow, handle, indent=2, ensure_ascii=True)
        except OSError as exc:
            self._set_status(f"Save failed: {exc}")
            return

        self._set_status(f"Workflow saved: {path}")

    def _refresh_graph_view(self) -> None:
        graph = self._workflow.get("graph", {"nodes": [], "edges": []})
        nodes, edges = graph_counts(graph)
        if self._summary_var is not None:
            self._summary_var.set(f"Nodes: {nodes} | Edges: {edges}")

        if self._node_list is None:
            return
        self._node_list.delete(0, "end")
        for node in graph.get("nodes", []):
            if isinstance(node, dict):
                node_id = node.get("id", "node")
                node_type = node.get("type", "")
                label = f"{node_id} ({node_type})" if node_type else str(node_id)
            else:
                label = str(node)
            self._node_list.insert("end", label)

    def _show_errors(self, errors: list[str]) -> None:
        if self._error_text is None:
            return
        self._error_text.configure(state="normal")
        self._error_text.delete("1.0", "end")
        if errors:
            for err in errors:
                self._error_text.insert("end", f"- {err}\n", "error")
        else:
            self._error_text.insert("end", "No validation errors.\n", "ok")
        self._error_text.configure(state="disabled")

    def _set_status(self, message: str) -> None:
        if self._status_var is not None:
            self._status_var.set(message)
