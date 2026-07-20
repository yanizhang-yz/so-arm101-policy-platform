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
