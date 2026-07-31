# Phase 2: Record and Inspect the Dataset

Date: 2026-07-21

Status: in progress

## Objective

Create a trustworthy LeRobot dataset for one instruction:

> Pick up the red cube and place it in the bowl.

Do not begin with all 50 demonstrations. First record a three-episode local
pilot, inspect its schema and timing, and prove that a rejected episode can be
discarded. Scale collection only after the pilot passes.

## What LeRobot Records

At each 30 Hz control step, `lerobot-record` performs this sequence:

```text
follower joint state + W1 image        leader joint positions
               |                               |
               v                               v
       robot.get_observation()          teleop.get_action()
               |                               |
               +---------------+---------------+
                               v
                    robot.send_action(action)
                               |
                               v
        dataset.add_frame(observation + action + task)
```

A **frame** is one synchronized training sample. An **episode** is the ordered
sequence of frames for one task attempt. The **dataset** is the collection of
episodes plus feature definitions, timestamps, task metadata, and encoded
camera video.

The action stored by this recorder is the leader-derived command associated
with that observation. During behavior-cloning training, the model learns to
predict actions like these from observations and the language instruction.

## Pilot Protocol

Record three successful episodes with the cube starting at:

1. `center`
2. `near_left`
3. `near_right`

Keep all other conditions fixed: W1 position, bowl position, lighting, task
wording, camera resolution, frame rate, and calibration.

The verified W1 recording mode is `640x360` at 30 FPS. Requesting `640x480`
causes LeRobot to receive 360-pixel-high frames that do not match its declared
feature shape, so the recording command must use the native height.

An accepted episode must:

- Begin with the follower in the documented neutral pose.
- Show both the cube and bowl clearly in the W1 image.
- Lift the cube clear of the table and release it inside the bowl.
- Finish within 20 seconds.
- Avoid human contact with the follower arm.
- Contain no camera, serial, or control-loop warning that invalidates timing.

The first episode starts immediately after the recorder connects. Arrange the
cube, bowl, follower pose, and leader pose before launching the command. The
session then follows this timeline:

```text
record episode 0 -> unrecorded reset -> record episode 1
                 -> unrecorded reset -> record episode 2 -> exit
```

Only move the cube by hand during an **unrecorded reset**. Finish the reset and
remove hands from the camera view before the next recording announcement.

## Recording Controls

- The recording and reset timers are maximums, not mandatory waits.
- During recording, press Right Arrow or `n` to accept and end the current
  episode early.
- During reset, press Right Arrow or `n` again when the next scene is ready to
  start the next episode early.
- Confirm each press by checking that the terminal prints
  `Right arrow key pressed. Exiting loop...`.
- Press Left Arrow or `r` to discard the current episode and record it again.
- Press Escape or `q` to stop the recording session.

Keep the recording terminal focused if LeRobot reports that it is using
terminal keyboard input. In LeRobot 0.6.0, stopping with `q` can still save the
partial current episode, so prefer `r` when an attempt should not enter the
dataset.

Keep Rerun disabled during this pilot so it cannot take keyboard focus and so
visualization does not add CPU work to the recording path. The W1 video is still
recorded and will be inspected after the session.

If an existing dataset root already contains a pilot, use a new root for the
next attempt. Do not overwrite the first pilot; it is useful debugging evidence.

## Three-Episode Local Pilot

Place the follower in a safe neutral pose, put the cube at `center`, keep the
bowl at its frozen location, and activate the virtual environment. First use
LeRobot's port-discovery workflow and export the locally resolved device paths
as `FOLLOWER_PORT` and `LEADER_PORT`; those paths belong in the shell
environment, not Git.

```bash
cd so-arm101-policy-platform
source .venv/bin/activate
```

Then run:

```bash
lerobot-record \
  --robot.type=so101_follower \
  --robot.port="$FOLLOWER_PORT" \
  --robot.id=follower_arm \
  --robot.cameras='{front: {type: opencv, index_or_path: 0, width: 640, height: 360, fps: 30}}' \
  --teleop.type=so101_leader \
  --teleop.port="$LEADER_PORT" \
  --teleop.id=leader_arm \
  --dataset.repo_id=yanizhang/so-arm101-red-cube-to-bowl-pilot \
  --dataset.root=datasets/phase-2/pilot-v1 \
  --dataset.single_task="Pick up the red cube and place it in the bowl." \
  --dataset.fps=30 \
  --dataset.episode_time_s=30 \
  --dataset.reset_time_s=30 \
  --dataset.num_episodes=3 \
  --dataset.video=true \
  --dataset.push_to_hub=false \
  --display_data=false
```

During each reset window, return the robot to its neutral pose, move the cube to
the next listed position, and return the cube from the bowl. Reset activity is
executed through teleoperation but is not written to the dataset. Press `n`
when the reset is complete instead of waiting for the 30-second maximum.

## Pilot Completion Gate

- [ ] Three episodes save without a traceback.
- [ ] All three videos show the complete task and the intended camera view.
- [ ] State and action features have the expected six joint values.
- [ ] Frame timestamps are monotonic and close to 30 Hz.
- [ ] Episode lengths agree with the actual task duration.
- [ ] One frame can be loaded through `LeRobotDataset` and inspected.
- [ ] A deliberately rejected attempt does not appear as an accepted episode.

After recording, the next repository tool will inspect feature names, tensor
shapes, episode lengths, timestamps, and camera frames before any Hub upload.
