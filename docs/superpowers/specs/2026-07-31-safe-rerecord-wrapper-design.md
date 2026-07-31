# Safe Re-record Wrapper Design

## Problem

LeRobot 0.6.0 records non-streaming video as temporary image files before
encoding them. When the operator presses `r`, `DatasetWriter.clear_episode_buffer()`
resets the data buffer but deletes temporary directories only for metadata
`image_keys`. Camera features recorded as video use `video_keys`, so stale frames
can survive a rejected attempt.

If the accepted replacement is shorter than the rejected attempt, the leftover
frames are appended to the accepted episode's video. Round 5 exposed this as 80
video frames without matching robot-state or action rows.

## Decision

Add a repository-owned wrapper around the installed `lerobot-record` entry
point. The wrapper keeps the standard command-line interface and recording loop,
but installs one narrow runtime patch before invoking LeRobot.

The patch replaces rejected-episode cleanup with this sequence:

1. Cancel an active streaming encoder, if present.
2. Wait for pending asynchronous image writes.
3. Determine the current episode index.
4. Delete temporary frame directories for every `image_key`, `video_key`, and
   `depth_key` without deleting an already encoded dataset video.
5. Create a fresh episode buffer through LeRobot's existing writer logic.

All recording, teleoperation, timing, encoding, metadata, and finalization
behavior remains owned by LeRobot.

## Operator Workflow

For an invalid current attempt, press `r`. Reset the environment during the
unrecorded reset window, then press `n` when ready. The replacement retains the
same episode index, and only its data and camera frames are saved.

Pressing `r` does not remove an episode that has already been saved. If a mistake
is discovered after the next episode begins, stop recording and run a separate,
backup-first dataset-editing workflow before collecting more data.

## Interface

The repository command will accept and forward the normal LeRobot arguments:

```bash
python scripts/record_dataset.py \
  --robot.type=so101_follower \
  --robot.port="$FOLLOWER_PORT" \
  --robot.id=follower_arm \
  --robot.cameras='{front: {type: opencv, index_or_path: 0, width: 640, height: 360, fps: 30}}' \
  --teleop.type=so101_leader \
  --teleop.port="$LEADER_PORT" \
  --teleop.id=leader_arm \
  --dataset.repo_id=yanizhang/so-arm101-red-cube-to-bowl-v1 \
  --dataset.root=datasets/phase-2/red-cube-to-bowl-v1 \
  --dataset.single_task="Pick up the red cube and place it in the bowl." \
  --dataset.fps=30 \
  --dataset.episode_time_s=60 \
  --dataset.reset_time_s=30 \
  --dataset.num_episodes=5 \
  --dataset.video=true \
  --dataset.push_to_hub=false \
  --display_data=false
```

No project-specific ports, camera indices, dataset paths, or task text are
embedded in the wrapper.

## Testing

The regression test will create temporary directories for both an image feature
and a video feature, invoke the patched cleanup behavior, and verify that:

- both temporary directories are removed;
- the episode buffer is reset;
- unrelated files outside those directories remain untouched;
- duplicate key categories do not cause cleanup failures.

The test must fail against LeRobot 0.6.0's original behavior before the patch is
implemented. The complete repository test suite and the 25-episode production
dataset inspector must pass afterward.

## Non-goals

- Forking or modifying the installed LeRobot package.
- Reimplementing the LeRobot recording loop.
- Automatically deleting already-saved episodes.
- Changing encoding modes or codecs.
- Uploading raw robot datasets to Git.
