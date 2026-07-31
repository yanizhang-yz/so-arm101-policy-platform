import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.inspect_dataset import inspect_dataset, main


TASK = "Pick up the red cube and place it in the bowl."


def write_dataset_fixture(
    root: Path,
    *,
    frame_indices: list[int] | None = None,
    timestamps: list[float] | None = None,
    action_first_value: float = 0.0,
    include_video: bool = True,
) -> Path:
    (root / "meta/episodes/chunk-000").mkdir(parents=True)
    (root / "data/chunk-000").mkdir(parents=True)

    info = {
        "codebase_version": "v3.0",
        "robot_type": "so_follower",
        "fps": 10,
        "total_episodes": 2,
        "total_frames": 4,
        "total_tasks": 1,
        "features": {
            "action": {"dtype": "float32", "shape": [6]},
            "observation.state": {"dtype": "float32", "shape": [6]},
        },
    }
    if include_video:
        info["features"]["observation.images.front"] = {
            "dtype": "video",
            "shape": [360, 640, 3],
            "info": {
                "video.height": 360,
                "video.width": 640,
                "video.fps": 10,
                "video.channels": 3,
            },
        }
    (root / "meta/info.json").write_text(json.dumps(info))

    tasks = pa.table({"task_index": [0], "task": [TASK]})
    pq.write_table(tasks, root / "meta/tasks.parquet")

    episode_columns = {
        "episode_index": [0, 1],
        "tasks": [[TASK], [TASK]],
        "length": [2, 2],
        "dataset_from_index": [0, 2],
        "dataset_to_index": [2, 4],
    }
    if include_video:
        episode_columns["videos/observation.images.front/from_timestamp"] = [0.0, 0.2]
        episode_columns["videos/observation.images.front/to_timestamp"] = [0.2, 0.4]
    episodes = pa.table(episode_columns)
    pq.write_table(episodes, root / "meta/episodes/chunk-000/file-000.parquet")

    vector_type = pa.list_(pa.float32(), 6)
    actions = pa.array(
        [
            [action_first_value, 1.0, 2.0, 3.0, 4.0, 5.0],
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            [3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        ],
        type=vector_type,
    )
    states = pa.array(
        [
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            [0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
            [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            [2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
        ],
        type=vector_type,
    )
    data = pa.table(
        {
            "action": actions,
            "observation.state": states,
            "timestamp": pa.array(timestamps or [0.0, 0.1, 0.0, 0.1], type=pa.float32()),
            "frame_index": frame_indices or [0, 1, 0, 1],
            "episode_index": [0, 0, 1, 1],
            "index": [0, 1, 2, 3],
            "task_index": [0, 0, 0, 0],
        }
    )
    pq.write_table(data, root / "data/chunk-000/file-000.parquet")
    return root


def valid_decoded_sample() -> dict[str, object]:
    return {
        "action": np.zeros((6,), dtype=np.float32),
        "observation.state": np.zeros((6,), dtype=np.float32),
        "observation.images.front": np.zeros((3, 360, 640), dtype=np.float32),
        "timestamp": np.asarray(0.0, dtype=np.float32),
        "frame_index": np.asarray(0),
        "episode_index": np.asarray(0),
        "index": np.asarray(0),
        "task_index": np.asarray(0),
        "task": TASK,
    }


def failure_details(report) -> str:
    return "\n".join(check.detail for check in report.checks if not check.passed)


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


def test_missing_frame_index_is_rejected(tmp_path: Path) -> None:
    root = write_dataset_fixture(tmp_path, frame_indices=[0, 2, 0, 1])

    report = inspect_dataset(root, 2, 10, sample_loader=lambda _: valid_decoded_sample())

    assert report.passed is False
    assert "contiguous" in failure_details(report)


def test_off_rate_timestamp_is_rejected(tmp_path: Path) -> None:
    root = write_dataset_fixture(tmp_path, timestamps=[0.0, 0.2, 0.0, 0.1])

    report = inspect_dataset(root, 2, 10, sample_loader=lambda _: valid_decoded_sample())

    assert report.passed is False
    assert "10 Hz" in failure_details(report)


def test_nan_action_is_rejected(tmp_path: Path) -> None:
    root = write_dataset_fixture(tmp_path, action_first_value=float("nan"))

    report = inspect_dataset(root, 2, 10, sample_loader=lambda _: valid_decoded_sample())

    assert report.passed is False
    assert "finite" in failure_details(report)


def test_incorrect_expected_episode_count_is_rejected(tmp_path: Path) -> None:
    root = write_dataset_fixture(tmp_path)

    report = inspect_dataset(root, 3, 10, sample_loader=lambda _: valid_decoded_sample())

    assert report.passed is False
    assert "expected 3 episodes" in failure_details(report)


def test_missing_video_feature_is_rejected_without_crashing(tmp_path: Path) -> None:
    root = write_dataset_fixture(tmp_path, include_video=False)

    report = inspect_dataset(root, 2, 10, sample_loader=lambda _: valid_decoded_sample())

    assert report.passed is False
    assert "video-backed camera" in failure_details(report)


def test_main_prints_passing_report_and_returns_zero(tmp_path: Path, capsys) -> None:
    root = write_dataset_fixture(tmp_path)

    exit_code = main(
        [
            "--root",
            str(root),
            "--expected-episodes",
            "2",
            "--expected-fps",
            "10",
        ],
        sample_loader=lambda _: valid_decoded_sample(),
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS" in output
    assert "Episode 0: 2 frames, 0.200 s" in output
    assert "observation.images.front: (3, 360, 640)" in output
    assert "HUMAN REVIEW REQUIRED" in output


def test_main_prints_quality_failures_and_returns_one(tmp_path: Path, capsys) -> None:
    root = write_dataset_fixture(tmp_path)

    exit_code = main(
        [
            "--root",
            str(root),
            "--expected-episodes",
            "3",
            "--expected-fps",
            "10",
        ],
        sample_loader=lambda _: valid_decoded_sample(),
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL" in output
    assert "expected 3 episodes" in output


def test_main_reports_unreadable_dataset_and_returns_two(tmp_path: Path, capsys) -> None:
    exit_code = main(
        [
            "--root",
            str(tmp_path / "missing"),
            "--expected-episodes",
            "3",
            "--expected-fps",
            "10",
        ]
    )

    assert exit_code == 2
    assert "error:" in capsys.readouterr().err
