"""Collect a non-secret snapshot of the local SO-ARM101 development host."""

from __future__ import annotations

import argparse
import glob
import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


def first_nonempty_line(value: str) -> str:
    return next((line.strip() for line in value.splitlines() if line.strip()), "")


def command_version(executable: str, *arguments: str) -> dict[str, object]:
    path = shutil.which(executable)
    if path is None:
        return {"available": False}
    result = subprocess.run(
        [path, *arguments],
        capture_output=True,
        check=False,
        text=True,
    )
    output = first_nonempty_line(result.stdout) or first_nonempty_line(result.stderr)
    return {
        "available": True,
        "path": path,
        "returncode": result.returncode,
        "version": output,
    }


def python_lerobot_version(python: Path | None) -> dict[str, object]:
    if python is None or not python.exists():
        return {"available": False}
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import json, lerobot, platform; "
            "print(json.dumps({'python': platform.python_version(), "
            "'lerobot': lerobot.__version__}))",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return {"available": False, "error": first_nonempty_line(result.stderr)}
    return {"available": True, **json.loads(result.stdout)}


def extract_camera_names(payload: dict[str, Any]) -> list[str]:
    cameras = payload.get("SPCameraDataType", [])
    return sorted(
        camera["_name"]
        for camera in cameras
        if isinstance(camera, dict) and isinstance(camera.get("_name"), str)
    )


def camera_names() -> list[str]:
    profiler = shutil.which("system_profiler")
    if profiler is None:
        return []
    result = subprocess.run(
        [profiler, "SPCameraDataType", "-json"],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return []
    return extract_camera_names(json.loads(result.stdout))


def serial_ports() -> list[str]:
    candidates = glob.glob("/dev/tty.usb*") + glob.glob("/dev/cu.usb*")
    return sorted(set(candidates))


def collect_inventory(legacy_python: Path | None) -> dict[str, object]:
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "tools": {
            "uv": command_version("uv", "--version"),
            "ffmpeg": command_version("ffmpeg", "-version"),
            "git": command_version("git", "--version"),
        },
        "devices": {
            "serial_ports": serial_ports(),
            "camera_names": camera_names(),
        },
        "active_lerobot": python_lerobot_version(Path(sys.executable)),
        "legacy_lerobot": python_lerobot_version(legacy_python),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--legacy-python", type=Path)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    report = collect_inventory(options.legacy_python)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
