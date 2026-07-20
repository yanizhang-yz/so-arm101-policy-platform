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

## Initial Read-Only Snapshot

- macOS 26.5 on Apple Silicon arm64
- system `python3` is 3.9.6 and must not receive project packages
- Homebrew `uv` is 0.11.8
- Homebrew `ffmpeg` is 8.1.1
- no SO-ARM101 serial devices were connected during the snapshot
- no external camera was visible during the snapshot
- the earlier LeRobot source checkout has user changes and must not be altered

## Connected Hardware Snapshot

On 2026-07-20, the intended final USB topology was verified with the leader,
follower, and one external camera connected through the powered WAVLINK dock:

- leader: `/dev/tty.usbmodem5B415319781`
- follower: `/dev/tty.usbmodem5B415325701`
- logical camera `front`: physical device `W1`, OpenCV index `0`
- camera capture: 1920x1080 at approximately 30 FPS during discovery

The recording configuration intentionally requests 640x480 at 30 FPS. OpenCV
camera indices can change after devices are disconnected, so the camera finder
must be rerun before recording if the USB topology changes.

Raw discovery frames are local-only because they can contain people and private
room imagery. They are excluded from Git; the repository records device metadata
and configuration instead.

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
- leader port, follower port, and camera are verified through the final dock
  topology
- the camera view must be tightened to the follower workspace before recording
- the follower power-cutoff procedure remains unverified
- the next physical command and its safety conditions are understood
