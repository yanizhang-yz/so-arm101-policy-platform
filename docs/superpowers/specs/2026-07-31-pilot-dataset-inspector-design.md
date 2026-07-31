# Pilot Dataset Inspector Design

## Problem

The three-episode pilot exists on disk, but its quality checks currently depend
on one-off terminal commands. Before recording approximately 50 demonstrations,
the repository needs one repeatable command that explains and validates the
LeRobot dataset contract.

## Goal

Provide one local command that inspects a LeRobot dataset and exits nonzero when
its machine-checkable quality gate fails:

```bash
python scripts/inspect_dataset.py \
  --root datasets/phase-2/pilot-v1 \
  --expected-episodes 3 \
  --expected-fps 30
```

The command must also load one real sample through `LeRobotDataset`. That proves
the framework can decode the stored camera video and expose the tensors that a
training job will consume.

## Design

The inspector has three independently understandable responsibilities:

1. Read LeRobot metadata and Parquet tables using structured parsers.
2. Validate dataset-wide and per-episode invariants.
3. Load sample zero through `LeRobotDataset` and report its tensor shapes.

The core validation function returns a structured report rather than printing
directly. The CLI formats that report for a human and returns exit code `0` for
a passing dataset, `1` for failed quality checks, or `2` for invalid arguments
or an unreadable dataset.

The report includes:

- dataset root, robot type, task, FPS, episode count, and total frame count;
- action, state, and camera feature names and shapes;
- each episode's frame count, duration, timestamp step, and video interval;
- whether action and state values are finite;
- whether frame indices are contiguous and timestamps are monotonic;
- the decoded sample's action, state, and image shapes;
- concise failures that name the violated invariant.

## Quality Rules

For this pilot, a passing machine inspection requires:

- exactly the requested number of episodes;
- the requested FPS in metadata;
- six-value `action` and `observation.state` features;
- at least one video-backed camera feature;
- finite action, state, and timestamp values;
- frame indices beginning at zero and increasing by one inside each episode;
- timestamps beginning near zero, increasing strictly, and remaining within a
  small tolerance of `1 / FPS`;
- metadata episode lengths and dataset index ranges matching Parquet rows;
- one sample successfully loaded through `LeRobotDataset` with matching tensor
  shapes.

Visual task success is deliberately not inferred by this tool. Whether the cube
was lifted and released into the bowl remains an explicit human review item.

## Errors

The command reports a concise error and exits with code `2` when required files
are absent, metadata cannot be parsed, Parquet cannot be read, or the dataset
cannot be loaded through LeRobot. Ordinary quality-rule failures produce a full
report and exit code `1` so all detected issues can be fixed together.

## Tests

Unit tests create small temporary metadata and Parquet fixtures. They verify:

- a valid two-episode fixture passes structural and timing checks;
- a missing frame index is rejected;
- a non-monotonic or off-rate timestamp is rejected;
- a NaN action value is rejected;
- an incorrect episode count is rejected;
- decoded sample shapes are included in the report;
- CLI exit codes distinguish quality failures from unreadable input.

The final integration check runs the command against
`datasets/phase-2/pilot-v1`, including a real AV1 frame decoded by
`LeRobotDataset`.

## Documentation And Privacy

The Phase 2 guide will record the command and its observed pilot results. Raw
episodes, decoded images, and private workspace imagery remain ignored by Git.
Only source code, tests, and summarized evidence are committed.

## Out Of Scope

- judging task success from pixels;
- modifying or deleting recorded episodes;
- uploading data to the Hugging Face Hub;
- generating train and validation splits;
- training or evaluating a policy;
- supporting legacy LeRobot dataset formats beyond the installed 0.6.0 stack.
