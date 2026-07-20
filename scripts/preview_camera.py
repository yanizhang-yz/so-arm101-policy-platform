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
