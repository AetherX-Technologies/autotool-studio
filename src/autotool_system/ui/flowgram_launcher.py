from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import webbrowser


class FlowGramLauncher:
    def __init__(
        self,
        repo_path: str | Path | None = None,
        demo: str = "demo-free-layout-simple",
    ) -> None:
        self._repo_path = Path(repo_path) if repo_path else Path("reference_project/flowgram.ai")
        self._demo = demo
        self._process: subprocess.Popen | None = None

    def start_demo(self) -> str:
        repo_path = self._repo_path.resolve()
        if not repo_path.exists():
            return f"FlowGram repo not found: {repo_path}"

        command = self._build_command(repo_path)
        if command is None:
            return "FlowGram launch requires Node.js (node) or Rush (rush)."

        if self._process and self._process.poll() is None:
            self._open_browser()
            return "FlowGram demo is already running."

        try:
            self._process = subprocess.Popen(command, cwd=repo_path)
        except FileNotFoundError as exc:
            return f"FlowGram launch failed: {exc}"

        self._open_browser()
        return "FlowGram demo starting. Check the console for logs."

    def _build_command(self, repo_path: Path) -> list[str] | None:
        rush = shutil.which("rush")
        if rush:
            return [rush, f"dev:{self._demo}"]

        install_script = repo_path / "common" / "scripts" / "install-run-rush.js"
        if install_script.exists() and shutil.which("node"):
            return ["node", str(install_script), f"dev:{self._demo}"]

        return None

    def _open_browser(self) -> None:
        webbrowser.open("http://localhost:3000", new=1)
