from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import base64
import io
import json
import os
import random
import shutil
import sys
import tempfile
import time
from uuid import uuid4

def _set_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except Exception:
        return
    try:
        set_context = ctypes.windll.user32.SetProcessDpiAwarenessContext
    except Exception:
        set_context = None
    if set_context is not None:
        try:
            if set_context(ctypes.c_void_p(-4)):
                return
        except Exception:
            pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_set_windows_dpi_awareness()

from fastapi import Body, FastAPI, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..core.workflow_builder import WorkflowBuilder, WorkflowError
from ..plugins import PluginManager
from ..utils.config_manager import ConfigManager, ConfigError
from ..utils.database import Database, DatabaseError
from ..utils.logger import configure_logging, get_logger
from ..version import __version__
from .state import ApiError, ApiState, RecorderSession, ReplaySession, RunManager, AutoClickerSession
from .state import _load_node_registry


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _error_response(error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "ok": False,
            "error": {"code": error.code, "message": str(error), "details": error.details},
        },
    )


def _get_pyautogui() -> Any:
    try:
        import pyautogui
    except Exception as exc:
        raise ApiError(f"pyautogui is not available: {exc}", code="INTERNAL_ERROR", status_code=500)
    return pyautogui


def _try_mss() -> Any | None:
    try:
        import mss
    except Exception:
        return None
    _set_windows_dpi_awareness()
    return mss


def _list_displays() -> tuple[list[dict[str, Any]], str]:
    mss = _try_mss()
    if mss is None:
        backend = _get_pyautogui()
        width, height = backend.size()
        return (
            [
                {
                    "id": 1,
                    "name": "Primary",
                    "left": 0,
                    "top": 0,
                    "width": width,
                    "height": height,
                    "primary": True,
                    "virtual": False,
                }
            ],
            "pyautogui",
        )

    displays: list[dict[str, Any]] = []
    with mss.mss() as sct:
        monitors = sct.monitors
        if monitors:
            virtual = monitors[0]
            displays.append(
                {
                    "id": 0,
                    "name": "All Displays",
                    "left": virtual["left"],
                    "top": virtual["top"],
                    "width": virtual["width"],
                    "height": virtual["height"],
                    "primary": False,
                    "virtual": True,
                }
            )
        for idx, mon in enumerate(monitors[1:], start=1):
            displays.append(
                {
                    "id": idx,
                    "name": f"Display {idx}",
                    "left": mon["left"],
                    "top": mon["top"],
                    "width": mon["width"],
                    "height": mon["height"],
                    "primary": idx == 1,
                    "virtual": False,
                }
            )
    return displays, "mss"


def _get_display(display_id: int | None) -> tuple[dict[str, int], str]:
    mss = _try_mss()
    if mss is None:
        if display_id not in (None, 0, 1):
            raise ApiError("Multi-monitor capture requires mss", code="BAD_REQUEST")
        backend = _get_pyautogui()
        width, height = backend.size()
        return {"left": 0, "top": 0, "width": width, "height": height}, "pyautogui"

    with mss.mss() as sct:
        monitors = sct.monitors
        target_id = 1 if display_id is None else display_id
        if target_id < 0 or target_id >= len(monitors):
            raise ApiError("Display not found", code="NOT_FOUND", status_code=404)
        return monitors[target_id], "mss"


def _resolve_region(region: tuple[int, int, int, int] | None, display_id: int | None) -> tuple[int, int, int, int] | None:
    if display_id is None:
        return region
    display, _ = _get_display(display_id)
    if region is None:
        return (display["left"], display["top"], display["width"], display["height"])
    return (
        display["left"] + region[0],
        display["top"] + region[1],
        region[2],
        region[3],
    )


def _capture_screen(
    display_id: int | None,
    region: tuple[int, int, int, int] | None,
) -> tuple[bytes, dict[str, int]]:
    mss = _try_mss()
    if mss is None:
        if display_id not in (None, 0, 1):
            raise ApiError("Multi-monitor capture requires mss", code="BAD_REQUEST")
        backend = _get_pyautogui()
        image = backend.screenshot(region=region)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        width, height = getattr(image, "size", (0, 0))
        return buffer.getvalue(), {"width": width, "height": height}

    with mss.mss() as sct:
        monitors = sct.monitors
        if not monitors:
            raise ApiError("No displays detected", code="INTERNAL_ERROR", status_code=500)
        virtual = monitors[0]
        target_id = 1 if display_id is None else display_id
        if target_id < 0 or target_id >= len(monitors):
            raise ApiError("Display not found", code="NOT_FOUND", status_code=404)
        display = monitors[target_id]

        target_left = display["left"] + (region[0] if region else 0)
        target_top = display["top"] + (region[1] if region else 0)
        target_width = region[2] if region else display["width"]
        target_height = region[3] if region else display["height"]

        if target_id != 0 and virtual:
            shot = sct.grab(virtual)
            try:
                from PIL import Image
            except Exception:
                shot = sct.grab(
                    {
                        "left": target_left,
                        "top": target_top,
                        "width": target_width,
                        "height": target_height,
                    }
                )
                import mss.tools

                png_bytes = mss.tools.to_png(shot.rgb, shot.size)
                return png_bytes, {"width": shot.width, "height": shot.height}

            image = Image.frombytes("RGB", shot.size, shot.rgb)
            crop_left = max(0, int(round(target_left - virtual["left"])))
            crop_top = max(0, int(round(target_top - virtual["top"])))
            crop_right = min(image.width, crop_left + int(round(target_width)))
            crop_bottom = min(image.height, crop_top + int(round(target_height)))
            cropped = image.crop((crop_left, crop_top, crop_right, crop_bottom))
            buffer = io.BytesIO()
            cropped.save(buffer, format="PNG")
            return buffer.getvalue(), {"width": cropped.width, "height": cropped.height}

        target = {
            "left": target_left,
            "top": target_top,
            "width": target_width,
            "height": target_height,
        }
        shot = sct.grab(target)
        import mss.tools

        png_bytes = mss.tools.to_png(shot.rgb, shot.size)
        return png_bytes, {"width": shot.width, "height": shot.height}

def _parse_region(value: Any) -> tuple[int, int, int, int] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        raise ApiError("Region must be list or 'x,y,w,h'", code="BAD_REQUEST")
    if len(parts) != 4:
        raise ApiError("Region must have 4 values", code="BAD_REQUEST")
    try:
        x, y, w, h = [int(float(item)) for item in parts]
    except (TypeError, ValueError) as exc:
        raise ApiError("Region values must be numbers", code="BAD_REQUEST") from exc
    if w <= 0 or h <= 0:
        raise ApiError("Region width and height must be positive", code="BAD_REQUEST")
    return (x, y, w, h)


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ApiError("Invalid boolean value", code="BAD_REQUEST")


def _box_to_dict(box: Any) -> dict[str, int]:
    if hasattr(box, "left"):
        left = int(getattr(box, "left"))
        top = int(getattr(box, "top"))
        width = int(getattr(box, "width"))
        height = int(getattr(box, "height"))
    else:
        left, top, width, height = [int(float(item)) for item in box[:4]]
    return {"x": left, "y": top, "width": width, "height": height}


def _locate_image(
    template_path: str,
    *,
    region: tuple[int, int, int, int] | None,
    confidence: float | None,
    grayscale: bool | None,
    attempts: int,
    interval_s: float,
    display_id: int | None,
) -> Any | None:
    backend = _get_pyautogui()
    use_mss = display_id is not None and _try_mss() is not None

    def run_locate(*, haystack: Any | None, region_arg: tuple[int, int, int, int] | None) -> Any | None:
        kwargs: dict[str, Any] = {}
        if region_arg is not None:
            kwargs["region"] = region_arg
        if confidence is not None:
            kwargs["confidence"] = confidence
        if grayscale is not None:
            kwargs["grayscale"] = grayscale
        try:
            if haystack is None:
                return backend.locateOnScreen(template_path, **kwargs)
            return backend.locate(template_path, haystack, **kwargs)
        except TypeError as exc:
            if confidence is not None and "confidence" in str(exc):
                kwargs.pop("confidence", None)
                if haystack is None:
                    return backend.locateOnScreen(template_path, **kwargs)
                return backend.locate(template_path, haystack, **kwargs)
            raise ApiError(str(exc), code="INTERNAL_ERROR", status_code=500) from exc
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(str(exc), code="INTERNAL_ERROR", status_code=500) from exc

    for idx in range(max(1, attempts)):
        if use_mss:
            png_bytes, _ = _capture_screen(display_id, region)
            try:
                from PIL import Image
            except Exception as exc:
                raise ApiError(
                    f"Pillow is required for screen matching: {exc}",
                    code="INTERNAL_ERROR",
                    status_code=500,
                ) from exc
            haystack = Image.open(io.BytesIO(png_bytes))
            haystack.load()
            box = run_locate(haystack=haystack, region_arg=None)
            if box:
                base_left, base_top = 0, 0
                if display_id is not None:
                    display, _ = _get_display(display_id)
                    base_left = display["left"]
                    base_top = display["top"]
                if region is not None:
                    base_left += region[0]
                    base_top += region[1]
                box_dict = _box_to_dict(box)
                return (
                    box_dict["x"] + base_left,
                    box_dict["y"] + base_top,
                    box_dict["width"],
                    box_dict["height"],
                )
        else:
            region_arg = _resolve_region(region, display_id)
            box = run_locate(haystack=None, region_arg=region_arg)
            if box:
                return box

        if idx < attempts - 1:
            time.sleep(max(0.0, interval_s))
    return None


def _ensure_config(config_path: Path) -> dict[str, Any]:
    manager = ConfigManager()
    if not config_path.exists():
        template = Path("config/templates/default.yaml")
        if template.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template, config_path)
    return manager.load(str(config_path))


def _load_state(
    *,
    config_path: Path,
    db_path: Path | None,
    plugin_path: Path,
) -> ApiState:
    config = _ensure_config(config_path)
    logging_cfg = config.get("logging", {})
    if isinstance(logging_cfg, Mapping):
        configure_logging(
            level=str(logging_cfg.get("level", "INFO")),
            log_file=logging_cfg.get("file"),
        )

    db = Database()
    path = db_path or Path(config.get("storage", {}).get("db_path", "data/automation.db"))
    db.connect(str(path))
    db.migrate()

    plugin_manager = PluginManager()
    plugin_manager.discover(plugin_path)

    node_registry = _load_node_registry(Path("config/flowgram_nodes.json"))

    state = ApiState(
        config_path=config_path,
        config=config,
        config_manager=ConfigManager(),
        db=db,
        workflow_builder=WorkflowBuilder(),
        plugin_manager=plugin_manager,
        run_manager=RunManager(db),
        recorder=RecorderSession(),
        replay=ReplaySession(),
        autoclicker=AutoClickerSession(),
        node_registry=node_registry,
    )
    return state

def create_app(
    *,
    config_path: str | Path | None = None,
    db_path: str | Path | None = None,
    plugin_path: str | Path | None = None,
) -> FastAPI:
    config_path = Path(
        config_path
        or os.environ.get("AUTOTOOL_CONFIG_PATH", "config/default.yaml")
    )
    plugin_path = Path(plugin_path or "plugins")
    db_path_path = Path(db_path) if db_path else None

    app = FastAPI(title="AutoTool System API", version=__version__)
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For local dev; restrict in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    state = _load_state(config_path=config_path, db_path=db_path_path, plugin_path=plugin_path)
    app.state.api = state
    logger = get_logger("autotool.api")

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return _error_response(exc)

    @app.exception_handler(ConfigError)
    async def config_error_handler(_: Request, exc: ConfigError) -> JSONResponse:
        return _error_response(ApiError(str(exc), code="VALIDATION_ERROR"))

    @app.exception_handler(DatabaseError)
    async def db_error_handler(_: Request, exc: DatabaseError) -> JSONResponse:
        return _error_response(ApiError(str(exc), code="INTERNAL_ERROR", status_code=500))

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        return _ok({"status": "ok", "version": __version__})

    @app.get("/api/v1/config")
    def get_config() -> dict[str, Any]:
        return _ok(state.config)

    @app.put("/api/v1/config")
    def update_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        state.config_manager.save(str(state.config_path), payload)
        state.config = payload
        return _ok(payload)

    @app.get("/api/v1/workflows")
    def list_workflows() -> dict[str, Any]:
        return _ok(state.db.list_workflows())

    @app.get("/api/v1/workflows/{workflow_id}")
    def get_workflow(workflow_id: str) -> dict[str, Any]:
        workflow = state.db.get_workflow(workflow_id)
        if workflow is None:
            raise ApiError("Workflow not found", code="NOT_FOUND", status_code=404)
        return _ok(workflow)

    @app.post("/api/v1/workflows")
    def save_workflow(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        errors = state.workflow_builder.validate(payload)
        if errors:
            raise ApiError("Validation failed", code="VALIDATION_ERROR", details=errors)
        state.db.save_workflow(payload)
        return _ok(payload)

    @app.delete("/api/v1/workflows/{workflow_id}")
    def delete_workflow(workflow_id: str) -> dict[str, Any]:
        deleted = state.db.delete_workflow(workflow_id)
        if not deleted:
            raise ApiError("Workflow not found", code="NOT_FOUND", status_code=404)
        return _ok({"id": workflow_id, "deleted": True})

    @app.post("/api/v1/workflows/validate")
    def validate_workflow(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        errors = state.workflow_builder.validate(payload)
        return _ok({"errors": errors})

    @app.post("/api/v1/workflows/{workflow_id}/compile")
    def compile_workflow(workflow_id: str) -> dict[str, Any]:
        workflow = state.db.get_workflow(workflow_id)
        if workflow is None:
            raise ApiError("Workflow not found", code="NOT_FOUND", status_code=404)
        try:
            actions = state.workflow_builder.compile(workflow)
        except WorkflowError as exc:
            raise ApiError(str(exc), code="VALIDATION_ERROR")
        return _ok([action.to_dict() for action in actions])

    @app.post("/api/v1/workflows/{workflow_id}/run")
    def run_workflow(
        workflow_id: str,
        payload: dict[str, Any] = Body(default_factory=dict),
    ) -> dict[str, Any]:
        workflow = state.db.get_workflow(workflow_id)
        if workflow is None:
            raise ApiError("Workflow not found", code="NOT_FOUND", status_code=404)
        try:
            actions = state.workflow_builder.compile(workflow)
        except WorkflowError as exc:
            raise ApiError(str(exc), code="VALIDATION_ERROR")
        speed = float(payload.get("speed", 1.0))
        stop_on_error = bool(payload.get("stop_on_error", False))
        entry = state.run_manager.start_workflow(
            workflow_id,
            [action.to_dict() for action in actions],
            speed=speed,
            stop_on_error=stop_on_error,
        )
        logger.info("Run started: %s", entry.run_id)
        return _ok(
            {
                "id": entry.run_id,
                "workflow_id": workflow_id,
                "status": entry.status,
                "started_at": entry.started_at,
            }
        )

    @app.post("/api/v1/runs/{run_id}/stop")
    def stop_run(run_id: str) -> dict[str, Any]:
        stopped = state.run_manager.stop_run(run_id)
        if not stopped:
            raise ApiError("Run not found", code="NOT_FOUND", status_code=404)
        return _ok({"id": run_id, "stopped": True})

    @app.get("/api/v1/runs")
    def list_runs() -> dict[str, Any]:
        return _ok(state.db.list_runs())

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        record = state.db.get_run(run_id)
        if record is None:
            raise ApiError("Run not found", code="NOT_FOUND", status_code=404)
        return _ok(record)

    @app.post("/api/v1/recording/start")
    def start_recording(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        record_moves = bool(payload.get("record_moves", True))
        min_move_interval = float(payload.get("min_move_interval", 0.0))
        state.recorder.start(record_moves=record_moves, min_move_interval=min_move_interval)
        return _ok({"status": state.recorder.status()})

    @app.post("/api/v1/recording/stop")
    def stop_recording() -> dict[str, Any]:
        events = state.recorder.stop()
        return _ok({"status": state.recorder.status(), "events": events})

    @app.get("/api/v1/recording/status")
    def recording_status() -> dict[str, Any]:
        return _ok({"status": state.recorder.status()})

    @app.post("/api/v1/autoclicker/start")
    def start_autoclicker(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        cps = float(payload.get("cps", 5.0))
        button = str(payload.get("button", "left"))
        duration = payload.get("duration")
        max_clicks = payload.get("max_clicks")
        jitter_ms = payload.get("jitter_ms")
        duration_val = float(duration) if duration is not None else None
        max_clicks_val = int(max_clicks) if max_clicks is not None else None
        jitter_val = float(jitter_ms) if jitter_ms is not None else None
        state.autoclicker.start(
            cps=cps,
            button=button,
            duration=duration_val,
            max_clicks=max_clicks_val,
            jitter_ms=jitter_val,
        )
        return _ok(state.autoclicker.status())

    @app.post("/api/v1/autoclicker/stop")
    def stop_autoclicker() -> dict[str, Any]:
        state.autoclicker.stop()
        return _ok(state.autoclicker.status())

    @app.get("/api/v1/autoclicker/status")
    def autoclicker_status() -> dict[str, Any]:
        return _ok(state.autoclicker.status())

    @app.get("/api/v1/vision/displays")
    def vision_displays() -> dict[str, Any]:
        displays, provider = _list_displays()
        return _ok({"displays": displays, "provider": provider})

    @app.post("/api/v1/vision/screenshot")
    def vision_screenshot(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        region = _parse_region(payload.get("region"))
        display_raw = payload.get("display")
        display_id = int(display_raw) if display_raw is not None else None
        png_bytes, size = _capture_screen(display_id, region)
        encoded = base64.b64encode(png_bytes).decode("ascii")
        return _ok(
            {
                "image": f"data:image/png;base64,{encoded}",
                "size": size,
            }
        )

    @app.post("/api/v1/vision/locate")
    def vision_locate(
        image: UploadFile = File(...),
        confidence: float | None = Form(None),
        region: str | None = Form(None),
        display: int | None = Form(None),
        grayscale: str | None = Form(None),
        attempts: int | None = Form(None),
        interval_ms: int | None = Form(None),
    ) -> dict[str, Any]:
        confidence_val = float(confidence) if confidence is not None else None
        if confidence_val is not None and not (0.0 < confidence_val <= 1.0):
            raise ApiError("Confidence must be between 0 and 1", code="BAD_REQUEST")
        region_val = _parse_region(region)
        display_id = int(display) if display is not None else None
        grayscale_val = _parse_bool(grayscale) if grayscale is not None else None
        attempts_val = int(attempts) if attempts is not None else 1
        interval_val = int(interval_ms) if interval_ms is not None else 200
        if attempts_val <= 0:
            raise ApiError("Attempts must be greater than 0", code="BAD_REQUEST")
        if interval_val < 0:
            raise ApiError("Interval must be non-negative", code="BAD_REQUEST")

        suffix = Path(image.filename or "template.png").suffix
        if not suffix:
            suffix = ".png"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(image.file, temp_file)
                temp_path = temp_file.name
            box = _locate_image(
                temp_path,
                region=region_val,
                confidence=confidence_val,
                grayscale=grayscale_val,
                attempts=attempts_val,
                interval_s=interval_val / 1000.0,
                display_id=display_id,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        if not box:
            return _ok({"found": False})
        box_dict = _box_to_dict(box)
        center = {
            "x": int(box_dict["x"] + box_dict["width"] / 2),
            "y": int(box_dict["y"] + box_dict["height"] / 2),
        }
        return _ok({"found": True, "box": box_dict, "center": center})

    @app.post("/api/v1/vision/click")
    def vision_click(
        image: UploadFile = File(...),
        confidence: float | None = Form(None),
        region: str | None = Form(None),
        display: int | None = Form(None),
        grayscale: str | None = Form(None),
        attempts: int | None = Form(None),
        interval_ms: int | None = Form(None),
        button: str = Form("left"),
        clicks: int = Form(1),
        click_interval_ms: int | None = Form(None),
        offset_x: int = Form(0),
        offset_y: int = Form(0),
        offset_jitter: float | None = Form(None),
    ) -> dict[str, Any]:
        confidence_val = float(confidence) if confidence is not None else None
        if confidence_val is not None and not (0.0 < confidence_val <= 1.0):
            raise ApiError("Confidence must be between 0 and 1", code="BAD_REQUEST")
        region_val = _parse_region(region)
        display_id = int(display) if display is not None else None
        grayscale_val = _parse_bool(grayscale) if grayscale is not None else None
        attempts_val = int(attempts) if attempts is not None else 1
        interval_val = int(interval_ms) if interval_ms is not None else 200
        if attempts_val <= 0:
            raise ApiError("Attempts must be greater than 0", code="BAD_REQUEST")
        if interval_val < 0:
            raise ApiError("Interval must be non-negative", code="BAD_REQUEST")
        if clicks <= 0:
            raise ApiError("Clicks must be greater than 0", code="BAD_REQUEST")
        if click_interval_ms is not None and click_interval_ms < 0:
            raise ApiError("Click interval must be non-negative", code="BAD_REQUEST")
        jitter_val = float(offset_jitter) if offset_jitter is not None else None
        if jitter_val is not None and jitter_val < 0:
            raise ApiError("Offset jitter must be non-negative", code="BAD_REQUEST")

        suffix = Path(image.filename or "template.png").suffix
        if not suffix:
            suffix = ".png"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(image.file, temp_file)
                temp_path = temp_file.name
            box = _locate_image(
                temp_path,
                region=region_val,
                confidence=confidence_val,
                grayscale=grayscale_val,
                attempts=attempts_val,
                interval_s=interval_val / 1000.0,
                display_id=display_id,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        if not box:
            return _ok({"found": False})
        box_dict = _box_to_dict(box)
        center_x = int(box_dict["x"] + box_dict["width"] / 2) + int(offset_x)
        center_y = int(box_dict["y"] + box_dict["height"] / 2) + int(offset_y)

        backend = _get_pyautogui()
        click_interval_s = (click_interval_ms or 0) / 1000.0
        if jitter_val is None and clicks == 1 and click_interval_s == 0:
            backend.click(x=center_x, y=center_y, clicks=clicks, interval=click_interval_s, button=button)
        else:
            for idx in range(clicks):
                jitter_x = random.uniform(-jitter_val, jitter_val) if jitter_val else 0.0
                jitter_y = random.uniform(-jitter_val, jitter_val) if jitter_val else 0.0
                target_x = int(round(center_x + jitter_x))
                target_y = int(round(center_y + jitter_y))
                backend.click(x=target_x, y=target_y, clicks=1, interval=0, button=button)
                if idx < clicks - 1 and click_interval_s > 0:
                    time.sleep(click_interval_s)

        return _ok(
            {
                "found": True,
                "box": box_dict,
                "center": {"x": center_x, "y": center_y},
                "clicked": True,
            }
        )

    @app.post("/api/v1/replay/start")
    def start_replay(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        items = payload.get("items")
        path = payload.get("path")
        if path:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            items = data.get("events", data)
        if not isinstance(items, list):
            raise ApiError("Replay items are required", code="BAD_REQUEST")
        speed = float(payload.get("speed", 1.0))
        stop_on_error = bool(payload.get("stop_on_error", False))
        state.replay.start(items, speed=speed, stop_on_error=stop_on_error)
        return _ok({"status": state.replay.status()})

    @app.post("/api/v1/replay/stop")
    def stop_replay() -> dict[str, Any]:
        state.replay.stop()
        return _ok({"status": state.replay.status()})

    @app.get("/api/v1/plugins")
    def list_plugins() -> dict[str, Any]:
        discovered = state.plugin_manager.list_discovered()
        loaded = set(state.plugin_manager.list_loaded())
        items = []
        for spec in discovered:
            items.append(
                {
                    "id": spec.plugin_id,
                    "name": spec.name,
                    "version": spec.version,
                    "description": spec.description,
                    "author": spec.author,
                    "loaded": spec.plugin_id in loaded,
                    "error": state.plugin_manager.get_error(spec.plugin_id),
                }
            )
        return _ok(items)

    @app.get("/api/v1/flowgram/nodes")
    def list_flowgram_nodes() -> dict[str, Any]:
        return _ok(state.node_registry)

    @app.get("/api/v1/flowgram/menu")
    def flowgram_menu() -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in state.node_registry:
            category = str(item.get("category", "未分组"))
            grouped.setdefault(category, []).append(item)
        menu = [{"category": key, "items": grouped[key]} for key in sorted(grouped.keys())]
        return _ok(menu)

    @app.post("/api/v1/flowgram/nodes/create")
    def create_flowgram_node(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        node_type = str(payload.get("type", "")).strip()
        if not node_type:
            raise ApiError("Node type is required", code="BAD_REQUEST")
        template = next((item for item in state.node_registry if item.get("type") == node_type), None)
        if template is None:
            raise ApiError("Node type not found", code="NOT_FOUND", status_code=404)
        node_id = f"node_{uuid4().hex[:8]}"
        node = {
            "id": node_id,
            "type": node_type,
            "data": template.get("defaultData", {}),
            "meta": {"position": payload.get("position", {"x": 100, "y": 100})},
        }
        return _ok(node)

    @app.post("/api/v1/plugins/load")
    def load_plugin(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        plugin_id = str(payload.get("id", "")).strip()
        if not plugin_id:
            raise ApiError("Plugin id is required", code="BAD_REQUEST")
        plugin = state.plugin_manager.load(plugin_id)
        if plugin is None:
            raise ApiError(
                state.plugin_manager.get_error(plugin_id) or "Load failed",
                code="INTERNAL_ERROR",
                status_code=500,
            )
        return _ok({"id": plugin_id, "loaded": True})

    @app.post("/api/v1/plugins/unload")
    def unload_plugin(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        plugin_id = str(payload.get("id", "")).strip()
        if not plugin_id:
            raise ApiError("Plugin id is required", code="BAD_REQUEST")
        unloaded = state.plugin_manager.unload(plugin_id)
        if not unloaded:
            raise ApiError("Plugin not loaded", code="NOT_FOUND", status_code=404)
        return _ok({"id": plugin_id, "loaded": False})

    return app


def run(
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    config_path: str | Path | None = None,
    db_path: str | Path | None = None,
    plugin_path: str | Path | None = None,
) -> None:
    import uvicorn

    if port is None:
        port = int(os.environ.get("AUTOTOOL_API_PORT", "18765"))
    app = create_app(config_path=config_path, db_path=db_path, plugin_path=plugin_path)
    uvicorn.run(app, host=host, port=port)
