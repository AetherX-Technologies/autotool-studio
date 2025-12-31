from autotool_system.cli import main
import sys

if __name__ == "__main__":
    if getattr(sys, "frozen", False) and len(sys.argv) == 1:
        sys.argv.append("ui")
    raise SystemExit(main())
