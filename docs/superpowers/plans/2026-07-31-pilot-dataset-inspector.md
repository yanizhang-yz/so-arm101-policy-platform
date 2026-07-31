# Pilot Dataset Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one repeatable command that validates a local LeRobot pilot dataset and proves that LeRobot can decode a real training sample.

**Architecture:** A single focused Python module reads JSON and Parquet files into a structured inspection report, then attaches one sample decoded through `LeRobotDataset`. Unit tests exercise temporary real files; only the slow video-decoding boundary is replaced with a small sample loader in unit tests, and the final integration run uses the real framework and pilot video.

**Tech Stack:** Python 3.12, LeRobot 0.6.0, PyArrow, NumPy, pytest

## Global Constraints

- Support the installed LeRobot 0.6.0 dataset format only.
- Keep raw datasets, decoded images, and workspace imagery out of Git.
- Treat visual task success as a human review item, not a machine claim.
- Return exit code `0` for pass, `1` for quality failures, and `2` for unreadable input.
- Use structured JSON and Parquet readers rather than parsing command output.
- Do not modify, delete, upload, split, or train on the inspected dataset.

---

### Task 1: Structural And Timing Validator

**Files:**
- Create: `tests/test_inspect_dataset.py`
- Create: `scripts/inspect_dataset.py`

**Interfaces:**
- Produces: `InspectionError`, `CheckResult`, `EpisodeSummary`, and `InspectionReport` dataclasses.
- Produces: `inspect_dataset(root: Path, expected_episodes: int, expected_fps: float, sample_loader: SampleLoader | None = None) -> InspectionReport`.
- Consumes: LeRobot `meta/info.json`, `meta/tasks.parquet`, `meta/episodes/**/*.parquet`, and `data/**/*.parquet`.

- [ ] **Step 1: Write a real temporary-dataset fixture and the valid-dataset test**

Create a helper in `tests/test_inspect_dataset.py` that writes a two-episode,
four-frame dataset with literal expected values. Then add:

```python
def test_valid_dataset_passes_structural_and_timing_checks(tmp_path: Path) -> None:
    root = write_dataset_fixture(tmp_path)

    report = inspect_dataset(
        root,
        expected_episodes=2,
        expected_fps=10,
        sample_loader=lambda _: valid_decoded_sample(),
    )

    assert report.passed is True
    assert report.total_frames == 4
    assert [episode.length for episode in report.episodes] == [2, 2]
    assert report.sample_shapes == {
        "action": (6,),
        "observation.state": (6,),
        "observation.images.front": (3, 360, 640),
    }
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python -m pytest -q tests/test_inspect_dataset.py::test_valid_dataset_passes_structural_and_timing_checks
```

Expected: collection fails because `scripts.inspect_dataset` does not exist.

- [ ] **Step 3: Implement metadata loading and the passing report**

In `scripts/inspect_dataset.py`, add frozen dataclasses and structured readers.
Read every sorted Parquet shard so the same code works when the full dataset
spans multiple files. Group data rows by `episode_index`, calculate duration and
timestamp deltas, and expose robot type, task text, and report fields without
printing inside the core function.

The default timestamp tolerance is:

```python
timestamp_tolerance_s = max(1e-4, 0.05 / expected_fps)
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
python -m pytest -q tests/test_inspect_dataset.py::test_valid_dataset_passes_structural_and_timing_checks
```

Expected: `1 passed`.

- [ ] **Step 5: Add one failing test for each structural mutation**

Add independent tests whose fixtures contain:

```python
frame_index = [0, 2]             # missing frame 1
timestamp = [0.0, 0.2]           # should be 0.1 at 10 FPS
action[1][0] = float("nan")       # invalid numeric value
expected_episodes = 3             # metadata contains only two
```

Each test must assert a semantic failure substring such as `contiguous`,
`10 Hz`, `finite`, or `expected 3 episodes`, not the full formatted message.

- [ ] **Step 6: Run the new tests and verify RED**

Run:

```bash
python -m pytest -q tests/test_inspect_dataset.py
```

Expected: the four mutation tests fail because the corresponding checks are not
implemented yet.

- [ ] **Step 7: Implement all structural quality checks**

Add checks for:

```text
metadata episode and frame totals
requested FPS and episode count
six-value action and state feature shapes
at least one video feature
task metadata readable through meta/tasks.parquet
finite action, state, and timestamp values
contiguous per-episode frame indices
strictly increasing timestamps near 1 / FPS
metadata lengths and half-open dataset index ranges
video interval duration equal to length / FPS
```

Collect all quality failures in the report instead of raising on the first one.
Raise `InspectionError` only when files are absent or cannot be parsed.

- [ ] **Step 8: Run the validator tests and verify GREEN**

Run:

```bash
python -m pytest -q tests/test_inspect_dataset.py
```

Expected: all Task 1 tests pass.

- [ ] **Step 9: Commit the structural validator**

```bash
git add scripts/inspect_dataset.py tests/test_inspect_dataset.py
git commit -m "feat: validate LeRobot dataset structure"
```

---

### Task 2: LeRobot Decoder And Command-Line Report

**Files:**
- Modify: `tests/test_inspect_dataset.py`
- Modify: `scripts/inspect_dataset.py`

**Interfaces:**
- Consumes: Task 1's `InspectionReport` and `inspect_dataset`.
- Produces: `load_lerobot_sample(root: Path) -> Mapping[str, object]`.
- Produces: `format_report(report: InspectionReport) -> str`.
- Produces: `main(argv: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write failing CLI behavior tests**

Add tests proving that:

```python
assert main(valid_args, sample_loader=valid_loader) == 0
assert "PASS" in capsys.readouterr().out

assert main(quality_failure_args, sample_loader=valid_loader) == 1
assert "FAIL" in capsys.readouterr().out

assert main(["--root", str(missing_root)]) == 2
assert "error:" in capsys.readouterr().err
```

Also assert the passing output includes episode lengths, durations, and decoded
sample shapes.

- [ ] **Step 2: Run the CLI tests and verify RED**

Run:

```bash
python -m pytest -q tests/test_inspect_dataset.py -k "main or report"
```

Expected: failure because `main` and `format_report` are missing.

- [ ] **Step 3: Implement the LeRobot loader and CLI**

The real loader must perform:

```python
dataset = LeRobotDataset(
    repo_id=f"local/{root.name}",
    root=root,
    video_backend="pyav",
)
sample = dataset[0]
```

Convert tensor `.shape` values into plain tuples for the report. The CLI accepts
`--root`, `--expected-episodes`, and `--expected-fps`, prints every check, and
prints `Visual task success: HUMAN REVIEW REQUIRED` even when all machine checks
pass.

- [ ] **Step 4: Run the complete test file and verify GREEN**

Run:

```bash
python -m pytest -q tests/test_inspect_dataset.py
```

Expected: all inspector tests pass.

- [ ] **Step 5: Run the repository test suite**

Run:

```bash
python -m pytest -q
```

Expected: all repository tests pass without warnings introduced by the new
code.

- [ ] **Step 6: Commit the decoder and CLI**

```bash
git add scripts/inspect_dataset.py tests/test_inspect_dataset.py
git commit -m "feat: inspect decoded LeRobot samples"
```

---

### Task 3: Real Pilot Audit And Phase 2 Evidence

**Files:**
- Modify: `docs/phases/02-record-and-inspect-dataset.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 2's command-line inspector.
- Produces: committed summarized evidence only; the pilot remains under the
  ignored `datasets/` tree.

- [ ] **Step 1: Run the inspector against the real three-episode pilot**

Run inside the managed workspace with a writable temporary cache:

```bash
HF_HOME=/tmp/so101-hf-cache \
HF_DATASETS_CACHE=/tmp/so101-hf-cache/datasets \
python scripts/inspect_dataset.py \
  --root datasets/phase-2/pilot-v1 \
  --expected-episodes 3 \
  --expected-fps 30
```

Expected: exit code `0`; 1,957 frames; episode lengths `649`, `686`, and `622`;
decoded image shape `(3, 360, 640)`; action and state shapes `(6,)`.

- [ ] **Step 2: Update the Phase 2 guide**

Add an `Inspect the Pilot` command section, record the observed episode lengths
and durations, check the six machine-verifiable completion boxes, and leave the
deliberate rejection experiment unchecked.

- [ ] **Step 3: Update the repository status**

Change the README dataset status from “three-episode pilot before the full
dataset” to “pilot validated; rejection-control exercise remains before full
collection.”

- [ ] **Step 4: Verify documentation and privacy boundaries**

Run:

```bash
git diff --check
git status --short
git check-ignore datasets/phase-2/pilot-v1/meta/info.json
python -m pytest -q
```

Expected: no whitespace errors, raw pilot path remains ignored, and all tests
pass.

- [ ] **Step 5: Commit the Phase 2 evidence**

```bash
git add docs/phases/02-record-and-inspect-dataset.md README.md
git commit -m "docs: record pilot dataset validation"
```
