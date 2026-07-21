# Phase 1: Hardware, Calibration, Camera, and Teleoperation

Date: 2026-07-21

Status: stability gate passed; short teleoperation video remains

## Verified Configuration

- LeRobot: 0.6.0 in the repository `.venv`
- Follower: SO-ARM101 at `/dev/tty.usbmodem5B415325701`
- Leader: SO-ARM101 at `/dev/tty.usbmodem5B415319781`
- Front camera: W1, resolved to OpenCV index `0` in this USB topology
- Camera mode: 640 x 480 at 30 frames per second
- USB topology: leader, follower, and camera connected through the powered hub

The OpenCV index is not treated as a permanent hardware identity. The repository
camera helper resolves the W1 by name because macOS camera indices can change
when devices are reconnected.

## Calibration Evidence

Both arms have calibration files under LeRobot's local Hugging Face cache. The
original known-working calibration was backed up before experimenting and was
restored after a new calibration attempt exposed a large wrist-center mismatch.
The restored files were verified byte-for-byte against their backups.

Calibration data and backups stay local because they describe this physical
pair of arms. They are intentionally excluded from Git.

## Official Teleoperation Baseline

The known-good baseline uses LeRobot's standard command without custom motion
limits, forced loop rates, or time limits:

```bash
.venv/bin/lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/tty.usbmodem5B415325701 \
  --robot.id=follower_arm \
  --teleop.type=so101_leader \
  --teleop.port=/dev/tty.usbmodem5B415319781 \
  --teleop.id=leader_arm
```

This baseline produced smooth leader-to-follower tracking.

## Integrated Camera and Visualization Run

Rerun is launched as a child executable, so the virtual environment must be
activated before running the command by name:

```bash
source .venv/bin/activate

lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/tty.usbmodem5B415325701 \
  --robot.id=follower_arm \
  --robot.cameras='{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}' \
  --teleop.type=so101_leader \
  --teleop.port=/dev/tty.usbmodem5B415319781 \
  --teleop.id=leader_arm \
  --display_data=true
```

Observed result:

- Leader and follower teleoperation worked normally.
- The W1 front-camera stream appeared in Rerun.
- The combined stack ran continuously for 16 minutes.
- No disconnect or unsafe motion occurred during the run.
- `Ctrl-C` shut down cleanly, all devices disconnected, and follower torque
  released.

This exceeds the roadmap's ten-minute stability requirement.

## Failure Investigated

The first camera-plus-Rerun attempt failed on the follower's initial synchronous
`Present_Position` read. Both serial device nodes remained available. A camera
run without Rerun then succeeded, and the full command succeeded on retry for
16 minutes. The failure was therefore recorded as a transient serial packet
error rather than evidence of a persistent camera, hub, calibration, or Rerun
conflict.

An earlier experiment also combined a lower loop rate with
`max_relative_target`. The follower became slow and stair-stepped because that
setting clamps per-update displacement; it is not a velocity controller or a
smoothing algorithm. Returning to the official baseline restored normal motion.

## Engineering Lessons

1. Establish the official known-good baseline before adding controls.
2. Change one variable at a time and measure its effect.
3. Separate camera, motor-bus, and visualization tests before combining them.
4. Keep hardware safety on the Mac; visualization failure must not redefine
   motor behavior.
5. Preserve known-good calibration before any recalibration experiment.

## Completion Checklist

- [x] Saved calibration data
- [x] Stable W1 camera preview
- [x] Leader-to-follower teleoperation
- [x] At least ten minutes without disconnects or unsafe motion
- [ ] Short teleoperation video

After the video is recorded, Phase 1 is complete and Phase 2 dataset recording
can begin.
