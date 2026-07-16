# Phase 0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze one measurable SO-ARM101 experiment, create an isolated LeRobot 0.6.0 edge environment, capture a reproducible local inventory, and stop safely at the physical hardware connection gate.

**Architecture:** Phase 0 produces configuration and evidence, not autonomous control. The known-working LeRobot 0.5.1 environment remains untouched; this repository receives a separate Python 3.12 and LeRobot 0.6.0 environment for current hardware, dataset, rollout, and asynchronous-inference interfaces.

**Tech Stack:** macOS arm64, Python 3.12, uv 0.11 or newer, LeRobot 0.6.0, pytest, JSON, standard-library Python.

## Global Constraints

- Do not modify `/Users/yanizhang/Documents/projects/lerobot-experiments` or its `.venv`.
- Do not run motor setup, calibration, teleoperation, or autonomous control while the arm is disconnected.
- Do not guess serial ports or camera indexes; represent unverified hardware as JSON `null` with `verified: false`.
- Do not install packages into `/usr/bin/python3`.
- Do not commit secrets, hostnames, Hugging Face tokens, camera images, calibration data, or local virtual environments.
- Use LeRobot type strings exactly: `so101_follower` and `so101_leader`.
- End each task with a focused verification and one small commit.
- Push all commits after the Phase 0 software-only checkpoint is verified.

---

## Task 1: Freeze the Experiment and Hardware Gate

**Files:**

- Create: `configs/experiments/red-cube-to-bowl-v1.json`
- Create: `docs/phases/00-foundation.md`

**Interfaces:**

- Consumes: the approved roadmap and known SO-ARM101 leader/follower setup.
- Produces: one machine-readable experiment definition and one human-readable Phase 0 lesson.

- [ ] Create `configs/experiments/red-cube-to-bowl-v1.json` with this exact content:

```json
{
  "schema_version": 1,
  "experiment_id": "so-arm101-red-cube-to-bowl-v1",
  "status": "hardware_pending",
  "task": {
    "instruction": "Pick up the red cube and place it in the bowl.",
    "timeout_s": 30,
    "object": "red cube",
    "destination": "bowl",
    "start_positions": [
      "near_left",
      "far_left",
      "center",
      "near_right",
      "far_right"
    ],
    "target_episodes": 50,
    "episodes_per_position": 10,
    "success_criteria": [
      "The gripper lifts the red cube clear of the work surface.",
      "The robot releases the red cube completely inside the bowl.",
      "The task finishes within 30 seconds without human contact with the follower arm."
    ],
    "failure_criteria": [
      "The cube is not released completely inside the bowl.",
      "The task exceeds 30 seconds.",
      "The operator performs an emergency stop or touches the follower arm.",
      "The robot, camera, recorder, or control process disconnects."
    ]
  },
  "hardware": {
    "robot_model": "SO-ARM101",
    "follower": {
      "lerobot_type": "so101_follower",
      "id": "follower_arm",
      "port": null,
      "verified": false
    },
    "leader": {
      "lerobot_type": "so101_leader",
      "id": "leader_arm",
      "port": null,
      "verified": false
    },
    "camera": {
      "name": "front",
      "type": "opencv",
      "index_or_path": null,
      "width": 640,
      "height": 480,
      "fps": 30,
      "verified": false
    },
    "emergency_stop": {
      "method": "operator removes follower motor power",
      "verified": false
    }
  },
  "software": {
    "legacy_reference": {
      "python": "3.12.13",
      "lerobot": "0.5.1",
      "environment": "~/Documents/projects/lerobot-experiments/.venv",
      "read_only": true
    },
    "edge": {
      "os": "macOS arm64",
      "python": "3.12",
      "lerobot": "0.6.0",
      "environment": ".venv"
    },
    "training": {
      "provider": "RunPod",
      "gpu": "NVIDIA A100 80 GB",
      "device": "cuda"
    }
  },
  "artifacts": {
    "dataset_repo": "yanizhang/so-arm101-red-cube-to-bowl-v1",
    "policy_repo": "yanizhang/smolvla-so-arm101-red-cube-to-bowl-v1"
  }
}
```

- [ ] Create `docs/phases/00-foundation.md` containing these sections and facts:

```markdown
# Phase 0: Foundation

## Question

Can we describe and reproduce the experiment before changing software or moving
the robot?

## Why This Phase Exists

Robot-learning failures cross hardware, data, model, runtime, and network
boundaries. Phase 0 records which components and versions are actually present so
later failures can be assigned to the correct layer.

## Frozen Experiment

The first task is one red cube into one bowl within 30 seconds. We collect 50
successful demonstrations across five marked cube positions, ten per position.
The exact machine-readable definition is in
`configs/experiments/red-cube-to-bowl-v1.json`.

## Version Decision

The earlier environment at `~/Documents/projects/lerobot-experiments/.venv` uses
Python 3.12.13 and LeRobot 0.5.1 and previously completed leader-to-follower
teleoperation. It is a read-only rollback reference.

This project uses a separate Python 3.12 environment with LeRobot 0.6.0. The new
stable release is selected because it contains the current rollout, dependency,
dataset, and deployment interfaces we intend to learn. Isolation means an upgrade
cannot destroy the known-working environment.

## Current Read-Only Snapshot

- macOS 26.5 on Apple Silicon arm64
- system `python3` is 3.9.6 and must not receive project packages
- Homebrew `uv` is 0.11.8
- Homebrew `ffmpeg` is 8.1.1
- no SO-ARM101 serial devices were connected during the snapshot
- no external camera was visible during the snapshot
- the earlier LeRobot source checkout has user changes and must not be altered

## Safety Gate

Before motor commands, the operator must verify the follower power cutoff, clear
the workspace, identify leader and follower ports by disconnecting one device at
a time, and confirm that the configured IDs still locate valid calibration files.

Phase 0 does not run motor setup, calibration, teleoperation, or autonomous
control.

## Completion Gate

- the experiment JSON is valid
- the isolated LeRobot environment imports successfully
- the local inventory report is reproducible and contains no secrets
- leader port, follower port, and camera remain explicitly unverified until the
  hardware is connected
- the next physical command and its safety conditions are understood
```

- [ ] Verify both documents:

```bash
python3 -m json.tool configs/experiments/red-cube-to-bowl-v1.json >/dev/null
git diff --check
```

Expected: both commands exit with code 0.

- [ ] Commit:

```bash
git add configs/experiments/red-cube-to-bowl-v1.json docs/phases/00-foundation.md
git commit -m "docs: freeze Phase 0 experiment"
```

## Task 2: Create the Isolated Edge Environment

**Files:**

- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `uv.lock`

**Interfaces:**

- Consumes: Homebrew `uv` and Python 3.12.
- Produces: `.venv` containing LeRobot 0.6.0 hardware and core-script dependencies plus pytest.

- [ ] Create `.python-version`:

```text
3.12
```

- [ ] Create `pyproject.toml`:

```toml
[project]
name = "so-arm101-learning-lab"
version = "0.1.0"
description = "Reproducible SO-ARM101 SmolVLA learning environment"
requires-python = ">=3.12,<3.13"
dependencies = [
  "lerobot[core_scripts,feetech]==0.6.0",
]

[dependency-groups]
dev = [
  "pytest>=8.3,<10",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] Resolve and install without touching the legacy environment:

```bash
uv sync
```

Expected: `.venv` and `uv.lock` are created and dependency resolution succeeds.

- [ ] Verify exact runtime versions:

```bash
uv run python --version
uv run python -c 'import lerobot; print(lerobot.__version__)'
uv run pytest --version
```

Expected: Python reports 3.12.x, LeRobot reports 0.6.0, and pytest reports a version from 8.3 through 9.x.

- [ ] Commit only reproducible inputs and lock data:

```bash
git add .python-version pyproject.toml uv.lock
git commit -m "chore: pin Phase 0 LeRobot environment"
```

## Task 3: Add a Tested Local Inventory Probe

**Files:**

- Create: `scripts/__init__.py`
- Create: `scripts/phase0_probe.py`
- Create: `tests/test_phase0_probe.py`

**Interfaces:**

- Consumes: local commands and an optional legacy Python path.
- Produces: `collect_inventory(legacy_python: Path | None) -> dict[str, object]` and a JSON report without hostname or secrets.

- [ ] Create `tests/test_phase0_probe.py`:

```python
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
```

- [ ] Run the test and verify the module is absent:

```bash
uv run pytest -q tests/test_phase0_probe.py
```

Expected: collection fails because `scripts.phase0_probe` does not exist.

- [ ] Create an empty `scripts/__init__.py` and create `scripts/phase0_probe.py`:

```python
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
```

- [ ] Run focused tests:

```bash
uv run pytest -q tests/test_phase0_probe.py
```

Expected: `3 passed`.

- [ ] Commit:

```bash
git add scripts/__init__.py scripts/phase0_probe.py tests/test_phase0_probe.py
git commit -m "feat: add Phase 0 inventory probe"
```

## Task 4: Capture the Software-Only Baseline

**Files:**

- Create: `reports/phase-0/local-inventory.json`

**Interfaces:**

- Consumes: the tested inventory probe and both isolated Python environments.
- Produces: one dated, non-secret baseline report committed as Phase 0 evidence.

- [ ] Generate the report:

```bash
uv run python scripts/phase0_probe.py \
  --legacy-python /Users/yanizhang/Documents/projects/lerobot-experiments/.venv/bin/python \
  --output reports/phase-0/local-inventory.json
```

- [ ] Inspect and verify it:

```bash
python3 -m json.tool reports/phase-0/local-inventory.json
uv run pytest -q
git diff --check
```

Expected: valid JSON, `3 passed`, and no diff errors. The report should show no serial devices or external camera until the hardware is connected.

- [ ] Commit:

```bash
git add reports/phase-0/local-inventory.json
git commit -m "docs: capture Phase 0 local baseline"
```

## Physical Hardware Gate

Stop software-only execution here. With both arm controller boards and the camera
connected, powered correctly, and the follower workspace clear, the next read-only
commands are:

```bash
uv run lerobot-find-port
uv run lerobot-find-cameras
```

The operator must identify leader and follower by disconnecting one controller at
a time. Only after those values are copied into the experiment JSON and the power
cutoff is tested may Phase 1 calibration and teleoperation begin.
