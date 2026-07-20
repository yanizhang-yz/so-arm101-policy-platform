# Name-Resolved Camera Preview Design

## Problem

macOS assigns camera indices separately for OpenCV and AVFoundation, and either
API can reorder its indices after devices reconnect. A hard-coded `ffplay` index
opened the MacBook camera after `W1` moved from AVFoundation index 1 to index 0.

## Goal

Provide one command that finds the current AVFoundation index for a camera by
its exact device name and opens a live preview:

```bash
uv run python scripts/preview_camera.py --name W1
```

The command defaults to 640x480 at 30 FPS and exits when the operator presses
`q` in `ffplay`.

## Design

The utility has two independently testable responsibilities:

1. Run FFmpeg's AVFoundation device-list command and parse only the video-device
   section into `{device_name: index}` data.
2. Resolve the requested exact name and invoke `ffplay` with the discovered
   index, requested frame rate and size, `uyvy422` input, and no audio device.

The parser will not treat an audio device named `W1` as a video camera. The
process will print the resolved name and index before starting the preview.

## Errors

The utility exits with a concise nonzero error when:

- `ffmpeg` or `ffplay` is unavailable;
- FFmpeg device discovery fails without producing a usable video list;
- the requested camera name is absent;
- the requested camera name appears more than once;
- width, height, or FPS is not positive.

The missing-camera error includes the available video-device names so the
operator can correct the name without reading raw FFmpeg output.

## Tests

Unit tests use recorded FFmpeg text rather than physical cameras. They verify:

- `W1` resolves correctly when its index is 1;
- `W1` resolves correctly after moving to index 0;
- an audio entry named `W1` is ignored;
- a missing camera produces an informative error;
- invalid numeric preview settings are rejected.

One manual verification launches the preview against the connected W1 camera.

## Documentation And Privacy

The Phase 0 guide will replace the hard-coded index command with the
name-resolving command. Preview frames remain local-only and ignored by Git.

## Out Of Scope

- changing LeRobot's own OpenCV camera configuration;
- persisting a numeric AVFoundation index;
- recording video or datasets;
- selecting cameras through a graphical interface.
