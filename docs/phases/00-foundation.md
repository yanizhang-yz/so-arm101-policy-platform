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
