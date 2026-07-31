# Phase 2: Record and Inspect the Dataset

Started: 2026-07-21

Completed: 2026-07-31

Status: complete

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
- Finish within the 60-second pilot recording window. After the recording
  workflow is comfortable, practice smoother demonstrations toward the
  experiment's 30-second evaluation target.
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
  The repository wrapper removes both its robot-data buffer and temporary
  camera frames before the replacement begins.
- Press Escape or `q` to stop the recording session.

Keep the recording terminal focused if LeRobot reports that it is using
terminal keyboard input. In LeRobot 0.6.0, stopping with `q` can still save the
partial current episode, so prefer `r` when an attempt should not enter the
dataset.

`r` applies only to the current buffered episode, including its following
reset window. If a mistake is discovered after the next episode has begun,
stop recording and repair the saved dataset from a backup before continuing.

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
python scripts/record_dataset.py \
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
  --dataset.episode_time_s=60 \
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

## Inspect the Pilot

Run the quality gate before scaling collection:

```bash
python scripts/inspect_dataset.py \
  --root datasets/phase-2/pilot-v1 \
  --expected-episodes 3 \
  --expected-fps 30
```

The inspector reads the JSON and Parquet dataset contract, validates every
episode's frame indices and timestamps, and loads sample zero through
`LeRobotDataset`. It does not infer task success from pixels; the operator must
still review the video.

The validated pilot contains 1,957 frames:

| Episode | Frames | Duration |
|---|---:|---:|
| 0 | 649 | 21.633 s |
| 1 | 686 | 22.867 s |
| 2 | 622 | 20.733 s |

The decoded sample has action shape `(6,)`, state shape `(6,)`, and W1 image
shape `(3, 360, 640)`. All numeric values are finite, frame indices are
contiguous, and timestamps advance at 30 Hz.

## Pilot Completion Gate

- [x] Three episodes save without a traceback.
- [x] All three videos show the complete task and the intended camera view.
- [x] State and action features have the expected six joint values.
- [x] Frame timestamps are monotonic and close to 30 Hz.
- [x] Episode lengths agree with the actual task duration.
- [x] One frame can be loaded through `LeRobotDataset` and inspected.
- [x] A deliberately rejected attempt does not appear as an accepted episode.

## Rejection-Control Evidence

The rejection test used the separate local root
`datasets/phase-2/rejection-control-v1`. The operator recorded a short invalid
attempt, pressed `r`, completed the unrecorded reset, and then recorded one
successful replacement.

Inspection found exactly one accepted episode with 684 frames and a 22.800-second
video. Its frame indices are contiguous, its timestamps advance at 30 Hz, and a
real sample decodes through `LeRobotDataset`. Visual review confirms that the
only saved video begins with the cube on the table and ends with it in the bowl;
the rejected buffer is absent.

Round 5 later exposed a longer-rejection edge case in LeRobot 0.6.0. Its
non-streaming cleanup removed temporary `image_keys` but not `video_keys`; the
first control passed only because the successful replacement was longer and
overwrote every rejected frame. The repository's `record_dataset.py` wrapper
now deletes both categories before delegating to LeRobot's original cleanup.

The pilot quality gate is complete. Full dataset collection can now begin while
the pilot and rejection-control roots remain local, ignored evidence.

## Full Collection Matrix

The production dataset contains 50 accepted episodes arranged as ten rounds of
five positions. The exact episode order and episode-level train/validation split
are stored in
`configs/experiments/red-cube-to-bowl-v1-collection.csv`.

Define positions in the W1 camera view with `center` at the pilot cube location.
Left and right follow the W1 image; near and far are measured relative to the
follower base. Begin with 5 cm offsets from center and move a mark inward only if
the power-off reachability rehearsal finds an unsafe or unreachable pose:

```text
farther from follower base

far_left          far_right
          center
near_left         near_right

nearer to follower base
```

Freeze the five cube marks, bowl mark, camera mount, lighting, instruction,
calibration, and neutral pose for all rounds. Record one round per process. A
failed attempt is re-recorded with `r` through `scripts/record_dataset.py` and
never consumes an episode index.

Rounds 5 and 10 form the ten-episode validation split. All other complete
episodes form the 40-episode training split; frames from one episode are never
divided across splits.

## Final Collection Evidence

The completed local dataset is stored at
`datasets/phase-2/red-cube-to-bowl-v1`. Raw data remains outside Git.

| Split | Episodes | Frames | Duration | Each start position |
|---|---:|---:|---:|---:|
| Training | 40 | 22,500 | 750.0 s | 8 episodes |
| Validation | 10 | 5,436 | 181.2 s | 2 episodes |
| Total | 50 | 27,936 | 931.2 s | 10 episodes |

The final quality gate was:

```bash
HF_HOME=/tmp/so101-hf-cache \
HF_DATASETS_CACHE=/tmp/so101-hf-cache/datasets \
python scripts/inspect_dataset.py \
  --root datasets/phase-2/red-cube-to-bowl-v1 \
  --expected-episodes 50 \
  --expected-fps 30
```

It passed all of these checks:

- Metadata reports 50 episodes, 27,936 frames, one task, and 30 Hz.
- Every episode has contiguous frame indices and monotonic 30 Hz timestamps.
- Every episode's video interval exactly matches its robot-data length.
- All action and observation-state values are finite six-joint vectors.
- A real sample decodes with action shape `(6,)`, state shape `(6,)`, and
  camera shape `(3, 360, 640)`.
- Each round's video frame count exactly equals the sum of its five episode
  lengths.
- Start/end contact sheets for all 50 episodes show a staged cube at the start
  and the cube released in the bowl at the end.
- The collection matrix joins one-to-one with dataset episode metadata and
  produces exactly 40 training and 10 validation episodes.
- Each of the five start positions appears eight times in training and twice
  in validation.

Round 5 required a documented repair after the inspector found 80 stale frames
from a rejected attempt. The accepted robot data was preserved, the stale video
tail was removed, affected timestamps were corrected, and the repaired dataset
passed the same structural, decode, frame-count, and visual checks. The original
local evidence remains at
`datasets/phase-2/red-cube-to-bowl-v1-round5-contaminated-backup`.

LeRobot's `meta/info.json` still exposes the physical collection as one
`train: 0:50` range. The collection CSV is the authoritative logical 40/10
episode split. The training workflow must materialize or explicitly select
those episode indices before fitting SmolVLA; random frame-level splitting is
not allowed.
