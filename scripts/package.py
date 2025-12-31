from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Package AutoTool System with PyInstaller")
    parser.add_argument("--name", default="autotool", help="Executable name")
    parser.add_argument("--dist", default="dist", help="Output directory")
    parser.add_argument("--build", default="build", help="Build work directory")
    parser.add_argument("--gui", action="store_true", help="Build without console window")
    args = parser.parse_args()

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        print("pyinstaller not found. Install with: pip install -e .[packaging]")
        return 1

    entry = Path("src/autotool_system/__main__.py")
    if not entry.exists():
        print(f"Entry not found: {entry}")
        return 1

    dist = Path(args.dist)
    build = Path(args.build)
    dist.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)

    hidden_imports = [
        "jaraco.functools",
        "jaraco.context",
        "jaraco.text",
    ]

    cmd = [
        pyinstaller,
        "--name",
        args.name,
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(dist),
        "--workpath",
        str(build),
        "--specpath",
        str(build),
    ]
    for module in hidden_imports:
        cmd.extend(["--hidden-import", module])
    if args.gui:
        cmd.append("--windowed")
    cmd.append(str(entry))

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
