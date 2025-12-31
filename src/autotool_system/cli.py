from __future__ import annotations

import argparse
import os

from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autotool",
        description="AutoTool System command line interface",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show CLI status")
    subparsers.add_parser("version", help="Show version")
    subparsers.add_parser("ui", help="Launch the GUI")
    serve_parser = subparsers.add_parser("serve", help="Start the local API server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=int(os.environ.get("AUTOTOOL_API_PORT", "18765")))
    serve_parser.add_argument("--config", default=None, help="Path to config file")
    serve_parser.add_argument("--db", default=None, help="Path to sqlite db")
    serve_parser.add_argument("--plugins", default=None, help="Path to plugins directory")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        print("AutoTool System: CLI ready (core modules not initialized)")
        return 0

    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "ui":
        from .ui.main_window import MainWindow

        MainWindow().show()
        return 0
    if args.command == "serve":
        from .api import run

        run(
            host=args.host,
            port=args.port,
            config_path=args.config,
            db_path=args.db,
            plugin_path=args.plugins,
        )
        return 0

    parser.print_help()
    return 0
