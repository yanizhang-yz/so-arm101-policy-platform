# Name-Resolved Camera Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested macOS camera-preview command that resolves `W1` by its current AVFoundation device name before launching `ffplay`.

**Architecture:** A pure parser converts FFmpeg's AVFoundation video-device section into typed camera records, and a resolver selects one exact name. A thin CLI performs dependency checks, validates preview settings, discovers devices, prints the selected mapping, and delegates live display to `ffplay`.

**Tech Stack:** Python 3.12, standard library (`argparse`, `dataclasses`, `re`, `shutil`, `subprocess`), pytest, FFmpeg/FFplay AVFoundation input.

## Global Constraints

- The public command is `uv run python scripts/preview_camera.py --name W1`.
- Default preview settings are 640x480 at 30 FPS with `uyvy422` input and no audio.
- Camera selection is an exact device-name match; numeric indices are never persisted.
- FFmpeg's audio-device section must never be parsed as video devices.
- Raw frames and room imagery remain local-only and excluded from Git.
- No new Python package dependency is allowed.

---

### Task 1: Parse And Resolve AVFoundation Cameras

**Files:**
- Create: `scripts/preview_camera.py`
- Create: `tests/test_preview_camera.py`

**Interfaces:**
- Consumes: FFmpeg AVFoundation device-list text from standard error.
- Produces: `CameraDevice(index: int, name: str)`, `parse_video_devices(output: str) -> list[CameraDevice]`, `resolve_camera(devices: list[CameraDevice], name: str) -> CameraDevice`, and `validate_preview_settings(width: int, height: int, fps: float) -> None`.

- [ ] **Step 1: Write failing parser and resolver tests**

```python
import pytest

from scripts.preview_camera import (
    CameraDevice,
    parse_video_devices,
    resolve_camera,
    validate_preview_settings,
)


DEVICE_LIST_INDEX_ONE = """
[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] MacBook Pro Camera
[AVFoundation indev @ 0x1] [1] W1
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] USB Audio Device
[AVFoundation indev @ 0x1] [1] W1
"""

DEVICE_LIST_INDEX_ZERO = """
[AVFoundation indev @ 0x2] AVFoundation video devices:
[AVFoundation indev @ 0x2] [0] W1
[AVFoundation indev @ 0x2] [1] MacBook Pro Camera
[AVFoundation indev @ 0x2] AVFoundation audio devices:
[AVFoundation indev @ 0x2] [0] W1
"""


@pytest.mark.parametrize(
    ("output", "expected_index"),
    [(DEVICE_LIST_INDEX_ONE, 1), (DEVICE_LIST_INDEX_ZERO, 0)],
)
def test_resolves_camera_after_avfoundation_reorders_devices(output, expected_index):
    devices = parse_video_devices(output)

    assert resolve_camera(devices, "W1") == CameraDevice(expected_index, "W1")


def test_parser_ignores_audio_devices():
    assert parse_video_devices(DEVICE_LIST_INDEX_ONE) == [
        CameraDevice(0, "MacBook Pro Camera"),
        CameraDevice(1, "W1"),
    ]


def test_missing_camera_lists_available_names():
    with pytest.raises(ValueError, match="Available video devices: MacBook Pro Camera, W1"):
        resolve_camera(parse_video_devices(DEVICE_LIST_INDEX_ONE), "front")


def test_duplicate_camera_name_is_rejected():
    devices = [CameraDevice(0, "W1"), CameraDevice(2, "W1")]

    with pytest.raises(ValueError, match="ambiguous"):
        resolve_camera(devices, "W1")


@pytest.mark.parametrize(
    ("width", "height", "fps"),
    [(0, 480, 30), (640, 0, 30), (640, 480, 0), (-1, 480, 30)],
)
def test_rejects_nonpositive_preview_settings(width, height, fps):
    with pytest.raises(ValueError, match="must be positive"):
        validate_preview_settings(width, height, fps)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_preview_camera.py
```

Expected: collection fails because `scripts.preview_camera` does not exist.

- [ ] **Step 3: Implement the minimal pure logic**

```python
"""Open a macOS camera preview after resolving its current device index."""

from __future__ import annotations

import re
from dataclasses import dataclass


VIDEO_HEADER = "AVFoundation video devices:"
AUDIO_HEADER = "AVFoundation audio devices:"
DEVICE_PATTERN = re.compile(r"\[(?P<index>\d+)\]\s+(?P<name>.+)$")


@dataclass(frozen=True)
class CameraDevice:
    index: int
    name: str


def parse_video_devices(output: str) -> list[CameraDevice]:
    devices: list[CameraDevice] = []
    in_video_section = False

    for line in output.splitlines():
        if VIDEO_HEADER in line:
            in_video_section = True
            continue
        if AUDIO_HEADER in line:
            break
        if not in_video_section:
            continue

        match = DEVICE_PATTERN.search(line)
        if match:
            devices.append(
                CameraDevice(
                    index=int(match.group("index")),
                    name=match.group("name").strip(),
                )
            )

    return devices


def resolve_camera(devices: list[CameraDevice], name: str) -> CameraDevice:
    matches = [device for device in devices if device.name == name]
    available = ", ".join(device.name for device in devices) or "none"
    if not matches:
        raise ValueError(f"Camera {name!r} not found. Available video devices: {available}")
    if len(matches) > 1:
        raise ValueError(f"Camera name {name!r} is ambiguous")
    return matches[0]


def validate_preview_settings(width: int, height: int, fps: float) -> None:
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("width, height, and fps must be positive")
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_preview_camera.py
```

Expected: all parser, resolver, and validation tests pass.

- [ ] **Step 5: Commit the tested selection logic**

```bash
git add scripts/preview_camera.py tests/test_preview_camera.py
git commit -m "feat: resolve AVFoundation camera by name"
```

---

### Task 2: Launch Preview And Correct The Guide

**Files:**
- Modify: `scripts/preview_camera.py`
- Modify: `tests/test_preview_camera.py`
- Modify: `docs/phases/00-foundation.md`

**Interfaces:**
- Consumes: `parse_video_devices`, `resolve_camera`, and `validate_preview_settings` from Task 1; installed `ffmpeg` and `ffplay` executables.
- Produces: `discover_video_devices(ffmpeg: str = "ffmpeg") -> list[CameraDevice]`, `build_ffplay_command(device: CameraDevice, width: int, height: int, fps: float, ffplay: str = "ffplay") -> list[str]`, and CLI `main(arguments: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write failing command-construction and discovery tests**

Append tests that patch only the process boundary:

```python
from subprocess import CompletedProcess
from unittest.mock import patch

from scripts.preview_camera import build_ffplay_command, discover_video_devices, main


def test_discovery_accepts_ffmpeg_nonzero_exit_when_device_list_is_present():
    completed = CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr=DEVICE_LIST_INDEX_ZERO,
    )
    with patch("scripts.preview_camera.subprocess.run", return_value=completed):
        assert discover_video_devices() == [
            CameraDevice(0, "W1"),
            CameraDevice(1, "MacBook Pro Camera"),
        ]


def test_builds_ffplay_command_for_resolved_device():
    assert build_ffplay_command(CameraDevice(0, "W1"), 640, 480, 30) == [
        "ffplay",
        "-f",
        "avfoundation",
        "-framerate",
        "30",
        "-video_size",
        "640x480",
        "-pixel_format",
        "uyvy422",
        "-i",
        "0:none",
    ]


def test_main_reports_missing_ffplay(capsys):
    with patch("scripts.preview_camera.shutil.which", side_effect=["/usr/bin/ffmpeg", None]):
        assert main(["--name", "W1"]) == 2

    assert "ffmpeg and ffplay must both be installed" in capsys.readouterr().err
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_preview_camera.py
```

Expected: import failure for `build_ffplay_command` and `discover_video_devices`.

- [ ] **Step 3: Implement discovery, command construction, and CLI**

Add standard-library imports and functions:

```python
import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence


def discover_video_devices(ffmpeg: str = "ffmpeg") -> list[CameraDevice]:
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        check=False,
        text=True,
    )
    devices = parse_video_devices(completed.stderr)
    if not devices:
        raise RuntimeError("FFmpeg did not report any AVFoundation video devices")
    return devices


def build_ffplay_command(
    device: CameraDevice,
    width: int,
    height: int,
    fps: float,
    ffplay: str = "ffplay",
) -> list[str]:
    validate_preview_settings(width, height, fps)
    fps_value = float(fps)
    fps_text = str(int(fps_value)) if fps_value.is_integer() else str(fps_value)
    return [
        ffplay,
        "-f",
        "avfoundation",
        "-framerate",
        fps_text,
        "-video_size",
        f"{width}x{height}",
        "-pixel_format",
        "uyvy422",
        "-i",
        f"{device.index}:none",
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Exact AVFoundation camera name")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=30.0)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    try:
        validate_preview_settings(options.width, options.height, options.fps)
        ffmpeg = shutil.which("ffmpeg")
        ffplay = shutil.which("ffplay")
        if ffmpeg is None or ffplay is None:
            raise RuntimeError("ffmpeg and ffplay must both be installed")
        device = resolve_camera(discover_video_devices(ffmpeg), options.name)
        print(f"Opening {device.name!r} at AVFoundation index {device.index}. Press q to quit.")
        command = build_ffplay_command(
            device,
            options.width,
            options.height,
            options.fps,
            ffplay,
        )
        return subprocess.run(command, check=False).returncode
    except (RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused and full tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_preview_camera.py
.venv/bin/python -m pytest -q
```

Expected: all new tests pass; the full suite reports no failures.

- [ ] **Step 5: Replace the hard-coded preview command in the guide**

Document:

```bash
uv run python scripts/preview_camera.py --name W1
```

Explain that the helper resolves the current AVFoundation index and that `q`
closes the preview before LeRobot opens the camera.

- [ ] **Step 6: Manually verify against connected W1**

Run:

```bash
uv run python scripts/preview_camera.py --name W1
```

Expected: the utility prints the current W1 index and opens the follower-workspace
view. Press `q` and confirm a zero exit status.

- [ ] **Step 7: Commit the CLI and documentation**

```bash
git add scripts/preview_camera.py tests/test_preview_camera.py docs/phases/00-foundation.md
git commit -m "feat: preview camera by device name"
```

---

### Task 3: Final Verification And Push

**Files:**
- Verify: `scripts/preview_camera.py`
- Verify: `tests/test_preview_camera.py`
- Verify: `docs/phases/00-foundation.md`

**Interfaces:**
- Consumes: the completed utility and its tests.
- Produces: a clean, synchronized `main` branch with the name-resolved preview workflow.

- [ ] **Step 1: Run final verification**

```bash
.venv/bin/python -m pytest -q
git diff --check
git status --short --branch
```

Expected: all tests pass, no whitespace errors, and only intentional commits are ahead of `origin/main`.

- [ ] **Step 2: Push the small commits**

```bash
git push origin main
```

- [ ] **Step 3: Confirm synchronization**

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Expected: `main...origin/main` with no divergence and matching revisions.
