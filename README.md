# AutoTool Studio

Local desktop automation system with recording, visual matching, and fast replay.

## Highlights

- Record and replay mouse/keyboard workflows locally
- Visual locate + click using template images
- Multi-monitor capture and region-based matching
- Auto clicker with jitter and caps
- History management, import/export, and PyAutoGUI script export
- Lightweight static UI prototype for real API testing

## Quick start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .
```

Optional, for full visual matching and multi-monitor capture:

```bash
python -m pip install mss opencv-python
```

Run the local API server:

```bash
python -m autotool_system serve
```

## Prototype UI (static)

The repo includes a static UI for end-to-end testing against the real API.

```bash
python -m http.server 8081 --directory apps/renderer
```

Open:

```
http://localhost:8081/prototype.html
```

Set the API base URL to `http://127.0.0.1:18765` in the UI if needed.

## Requirements

- Python 3.10+
- Windows/macOS/Linux (desktop input control requires local OS access)

See `requirements.txt` for core dependencies.

## Project layout

- `src/autotool_system/`: core packages and API server
- `apps/renderer/`: static UI prototype
- `tests/`: unit tests
- `scripts/`: helper scripts
- `config/`: configuration files
- `data/`: runtime data (local only)
- `docs/`: product and design documentation

## Notes

- Visual matching confidence uses OpenCV if available; it falls back gracefully without it.
- Multi-monitor capture uses `mss` when available.
- This project controls mouse/keyboard; run in a safe, local environment.
