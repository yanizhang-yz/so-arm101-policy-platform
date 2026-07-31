# Safe Re-record Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `r` reliably discard both robot data and non-streaming camera frames before LeRobot records a replacement episode.

**Architecture:** A repository script installs one narrow monkey patch on LeRobot 0.6.0's `DatasetWriter.clear_episode_buffer`, then invokes the official recorder entry point. The patch removes temporary video/depth frame directories and delegates all remaining cleanup and recording behavior to the original method.

**Tech Stack:** Python 3.12, LeRobot 0.6.0, pytest, pathlib, shutil

## Global Constraints

- Keep `lerobot[core_scripts,feetech]==0.6.0` unchanged.
- Do not modify files inside `.venv`.
- Do not reimplement LeRobot's recording loop or argument parser.
- Do not embed hardware ports or dataset paths in the wrapper.
- Keep raw datasets ignored by Git.

---

### Task 1: Safe Re-record Cleanup and Wrapper

**Files:**
- Create: `tests/test_record_dataset.py`
- Create: `scripts/record_dataset.py`

**Interfaces:**
- Consumes: `lerobot.datasets.dataset_writer.DatasetWriter.clear_episode_buffer(delete_images: bool = True)` and `lerobot.scripts.lerobot_record.main()`.
- Produces: `clear_episode_buffer_with_video_cleanup(writer, delete_images=True) -> None`, `install_safe_rerecord_patch() -> None`, and `main() -> int | None`.

- [ ] **Step 1: Write the failing cleanup regression test**

Create a real `DatasetWriter` with one image feature and one video feature. Create both temporary episode directories, invoke the new cleanup function, and require both directories to disappear while an unrelated sentinel survives:

```python
def test_cleanup_removes_image_and_video_temp_directories(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    image_dir = writer._get_image_file_dir(0, "observation.images.still")
    video_dir = writer._get_image_file_dir(0, "observation.images.front")
    image_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)
    (image_dir / "frame.png").touch()
    (video_dir / "frame.png").touch()
    sentinel = tmp_path / "keep.txt"
    sentinel.touch()

    clear_episode_buffer_with_video_cleanup(writer)

    assert not image_dir.exists()
    assert not video_dir.exists()
    assert sentinel.exists()
    assert writer.episode_buffer["size"] == 0
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_record_dataset.py
```

Expected: test collection fails because `scripts.record_dataset` does not exist.

- [ ] **Step 3: Implement the minimal cleanup patch and recorder wrapper**

Create `scripts/record_dataset.py` with these responsibilities:

```python
UPSTREAM_CLEAR_EPISODE_BUFFER = DatasetWriter.clear_episode_buffer


def clear_episode_buffer_with_video_cleanup(writer, delete_images: bool = True) -> None:
    if delete_images:
        writer._wait_image_writer()
        episode_index = normalize_episode_index(writer.episode_buffer["episode_index"])
        upstream_image_keys = set(writer._meta.image_keys)
        extra_keys = set(writer._meta.video_keys) | set(writer._meta.depth_keys)
        for camera_key in extra_keys - upstream_image_keys:
            frame_dir = writer._get_image_file_dir(episode_index, camera_key)
            if frame_dir.is_dir():
                shutil.rmtree(frame_dir)
    UPSTREAM_CLEAR_EPISODE_BUFFER(writer, delete_images)


def install_safe_rerecord_patch() -> None:
    DatasetWriter.clear_episode_buffer = clear_episode_buffer_with_video_cleanup


def main() -> int | None:
    install_safe_rerecord_patch()
    return lerobot_record.main()
```

Normalize scalar and NumPy-array episode indices the same way as LeRobot's
upstream method. Make installation idempotent so imports or repeated calls do
not wrap the method more than once.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
.venv/bin/pytest -q tests/test_record_dataset.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit the tested wrapper**

```bash
git add scripts/record_dataset.py tests/test_record_dataset.py
git commit -m "Add safe LeRobot rerecord wrapper"
```

---

### Task 2: Collection Workflow and Verification

**Files:**
- Modify: `docs/phases/02-record-and-inspect-dataset.md`

**Interfaces:**
- Consumes: `python scripts/record_dataset.py` from Task 1.
- Produces: the canonical Phase 2 recording command and operator recovery guidance.

- [ ] **Step 1: Update the documented recording entry point**

Replace `lerobot-record` with `python scripts/record_dataset.py` in the Phase 2
recording command. Explain that `r` discards the current attempt through the
safe wrapper, while a mistake noticed after the next episode begins requires the
operator to stop and repair the saved dataset before continuing.

- [ ] **Step 2: Run all automated tests**

Run:

```bash
.venv/bin/pytest -q
```

Expected: the entire repository suite passes.

- [ ] **Step 3: Re-run the production dataset quality gate**

Run:

```bash
HF_HOME=/tmp/so101-hf-cache \
HF_DATASETS_CACHE=/tmp/so101-hf-cache/datasets \
.venv/bin/python scripts/inspect_dataset.py \
  --root datasets/phase-2/red-cube-to-bowl-v1 \
  --expected-episodes 25 \
  --expected-fps 30
```

Expected: `Dataset inspection: PASS`, 25 episodes, and 13,751 frames.

- [ ] **Step 4: Commit the workflow update**

```bash
git add docs/phases/02-record-and-inspect-dataset.md
git commit -m "Document safe dataset rerecord workflow"
```

- [ ] **Step 5: Push both implementation commits**

```bash
git push origin main
```

Expected: local `main` and `origin/main` point to the same commit.
