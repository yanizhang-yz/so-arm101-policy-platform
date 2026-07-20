"""Open a macOS camera preview after resolving its current device index."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
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


def discover_video_devices(ffmpeg: str = "ffmpeg") -> list[CameraDevice]:
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-f",
            "avfoundation",
            "-list_devices",
            "true",
            "-i",
            "",
        ],
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
        print(
            f"Opening {device.name!r} at AVFoundation index {device.index}. "
            "Focus the preview and press q, or press Ctrl-C here, to quit."
        )
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
    except KeyboardInterrupt:
        print("\nPreview stopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
