import json
from pathlib import Path

from scripts import phase0_probe


def test_first_nonempty_line_ignores_blank_lines() -> None:
    assert phase0_probe.first_nonempty_line("\n\nuv 0.11.8\nmore") == "uv 0.11.8"


def test_extract_camera_names_reads_system_profiler_payload() -> None:
    payload = {
        "SPCameraDataType": [
            {"_name": "FaceTime HD Camera"},
            {"_name": "USB Camera"},
        ]
    }

    assert phase0_probe.extract_camera_names(payload) == [
        "FaceTime HD Camera",
        "USB Camera",
    ]


def test_write_report_creates_parseable_json(tmp_path: Path, monkeypatch) -> None:
    expected = {"platform": {"machine": "arm64"}, "devices": {"serial_ports": []}}
    monkeypatch.setattr(phase0_probe, "collect_inventory", lambda legacy_python: expected)
    output = tmp_path / "inventory.json"

    exit_code = phase0_probe.main(["--output", str(output)])

    assert exit_code == 0
    assert json.loads(output.read_text()) == expected
