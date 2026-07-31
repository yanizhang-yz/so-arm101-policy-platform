#!/usr/bin/env python3

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


class InspectionError(RuntimeError):
    """Raised when a dataset cannot be read well enough to inspect."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class EpisodeSummary:
    episode_index: int
    length: int
    duration_s: float
    mean_frame_period_s: float
    video_from_timestamp: float
    video_to_timestamp: float


@dataclass(frozen=True)
class InspectionReport:
    root: Path
    robot_type: str
    task: str
    fps: float
    total_episodes: int
    total_frames: int
    feature_shapes: dict[str, tuple[int, ...]]
    camera_features: tuple[str, ...]
    episodes: tuple[EpisodeSummary, ...]
    sample_shapes: dict[str, tuple[int, ...]]
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


SampleLoader = Callable[[Path], Mapping[str, object]]


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InspectionError(f"could not read {path}: {exc}") from exc


def _read_parquet_shards(root: Path, pattern: str) -> pa.Table:
    paths = sorted(root.glob(pattern))
    if not paths:
        raise InspectionError(f"no Parquet files matched {root / pattern}")
    try:
        return pa.concat_tables([pq.read_table(path) for path in paths])
    except (OSError, pa.ArrowException) as exc:
        raise InspectionError(f"could not read Parquet files for {pattern}: {exc}") from exc


def _shape(value: object) -> tuple[int, ...]:
    shape = getattr(value, "shape", None)
    if shape is None:
        return ()
    return tuple(int(size) for size in shape)


def _result(name: str, passed: bool, success: str, failure: str) -> CheckResult:
    return CheckResult(name=name, passed=bool(passed), detail=success if passed else failure)


def inspect_dataset(
    root: Path,
    expected_episodes: int,
    expected_fps: float,
    sample_loader: SampleLoader | None = None,
) -> InspectionReport:
    if expected_episodes <= 0:
        raise InspectionError("expected_episodes must be positive")
    if expected_fps <= 0:
        raise InspectionError("expected_fps must be positive")

    root = Path(root).expanduser().resolve()
    info = _read_json(root / "meta/info.json")
    tasks = _read_parquet_shards(root, "meta/tasks.parquet").to_pydict()
    episode_data = _read_parquet_shards(root, "meta/episodes/**/*.parquet").to_pydict()
    frame_data = _read_parquet_shards(root, "data/**/*.parquet").to_pydict()

    features = info["features"]
    feature_shapes = {
        name: tuple(int(size) for size in feature.get("shape", []))
        for name, feature in features.items()
    }
    camera_features = tuple(
        name for name, feature in features.items() if feature.get("dtype") == "video"
    )

    frame_episode_indices = np.asarray(frame_data["episode_index"], dtype=np.int64)
    frame_indices = np.asarray(frame_data["frame_index"], dtype=np.int64)
    dataset_indices = np.asarray(frame_data["index"], dtype=np.int64)
    timestamps = np.asarray(frame_data["timestamp"], dtype=np.float64)
    actions = np.asarray(frame_data["action"], dtype=np.float64)
    states = np.asarray(frame_data["observation.state"], dtype=np.float64)
    metadata_fps = float(info["fps"])
    timestamp_tolerance_s = max(1e-4, 0.05 / expected_fps)

    checks: list[CheckResult] = [
        _result(
            "expected_episode_count",
            int(info["total_episodes"]) == expected_episodes,
            f"found expected {expected_episodes} episodes",
            f"expected {expected_episodes} episodes, found {info['total_episodes']}",
        ),
        _result(
            "expected_fps",
            np.isclose(metadata_fps, expected_fps),
            f"metadata records {expected_fps:g} Hz",
            f"expected {expected_fps:g} Hz, metadata records {metadata_fps:g} Hz",
        ),
        _result(
            "metadata_episode_total",
            int(info["total_episodes"]) == len(episode_data["episode_index"]),
            "metadata episode total matches the episode table",
            "metadata episode total does not match the episode table",
        ),
        _result(
            "metadata_frame_total",
            int(info["total_frames"]) == len(frame_episode_indices),
            "metadata frame total matches the data table",
            "metadata frame total does not match the data table",
        ),
        _result(
            "action_shape",
            feature_shapes.get("action") == (6,) and actions.ndim == 2 and actions.shape[1] == 6,
            "action has six joint values",
            "action must have six joint values",
        ),
        _result(
            "state_shape",
            feature_shapes.get("observation.state") == (6,)
            and states.ndim == 2
            and states.shape[1] == 6,
            "observation.state has six joint values",
            "observation.state must have six joint values",
        ),
        _result(
            "video_feature",
            bool(camera_features),
            f"found video feature {camera_features[0]}" if camera_features else "found video feature",
            "at least one video-backed camera feature is required",
        ),
        _result(
            "task_metadata",
            bool(tasks.get("task")) and bool(str(tasks["task"][0]).strip()),
            f"task metadata is readable: {tasks['task'][0]}" if tasks.get("task") else "task metadata is readable",
            "task metadata is missing or empty",
        ),
        _result(
            "finite_actions",
            np.isfinite(actions).all(),
            "all action values are finite",
            "action values are not all finite",
        ),
        _result(
            "finite_states",
            np.isfinite(states).all(),
            "all observation.state values are finite",
            "observation.state values are not all finite",
        ),
        _result(
            "finite_timestamps",
            np.isfinite(timestamps).all(),
            "all timestamps are finite",
            "timestamp values are not all finite",
        ),
    ]

    episodes: list[EpisodeSummary] = []
    camera_key = camera_features[0] if camera_features else None
    video_from_key = f"videos/{camera_key}/from_timestamp" if camera_key else None
    video_to_key = f"videos/{camera_key}/to_timestamp" if camera_key else None
    for row, episode_index in enumerate(episode_data["episode_index"]):
        mask = frame_episode_indices == episode_index
        episode_timestamps = timestamps[mask]
        episode_frame_indices = frame_indices[mask]
        episode_dataset_indices = dataset_indices[mask]
        frame_periods = np.diff(episode_timestamps)
        metadata_length = int(episode_data["length"][row])
        dataset_from_index = int(episode_data["dataset_from_index"][row])
        dataset_to_index = int(episode_data["dataset_to_index"][row])
        video_from_timestamp = float(episode_data[video_from_key][row]) if video_from_key else 0.0
        video_to_timestamp = float(episode_data[video_to_key][row]) if video_to_key else 0.0
        expected_frame_indices = np.arange(len(episode_frame_indices))
        expected_dataset_indices = np.arange(dataset_from_index, dataset_to_index)

        episode_checks = [
            _result(
                f"episode_{episode_index}_length",
                metadata_length == len(episode_frame_indices),
                f"episode {episode_index} length matches {metadata_length} data rows",
                f"episode {episode_index} metadata length {metadata_length} does not match "
                f"{len(episode_frame_indices)} data rows",
            ),
            _result(
                f"episode_{episode_index}_frame_indices",
                np.array_equal(episode_frame_indices, expected_frame_indices),
                f"episode {episode_index} frame indices are contiguous",
                f"episode {episode_index} frame indices are not contiguous from zero",
            ),
            _result(
                f"episode_{episode_index}_dataset_range",
                np.array_equal(episode_dataset_indices, expected_dataset_indices),
                f"episode {episode_index} dataset index range matches metadata",
                f"episode {episode_index} dataset index range does not match metadata",
            ),
            _result(
                f"episode_{episode_index}_timestamp_origin",
                bool(len(episode_timestamps))
                and abs(float(episode_timestamps[0])) <= timestamp_tolerance_s,
                f"episode {episode_index} timestamps begin near zero",
                f"episode {episode_index} timestamps do not begin near zero",
            ),
            _result(
                f"episode_{episode_index}_timestamp_rate",
                bool(len(frame_periods))
                and bool(np.all(frame_periods > 0))
                and bool(
                    np.allclose(
                        frame_periods,
                        1.0 / expected_fps,
                        rtol=0.0,
                        atol=timestamp_tolerance_s,
                    )
                ),
                f"episode {episode_index} timestamps are monotonic at {expected_fps:g} Hz",
                f"episode {episode_index} timestamps are not monotonic at {expected_fps:g} Hz",
            ),
        ]
        if camera_key:
            episode_checks.append(
                _result(
                    f"episode_{episode_index}_video_interval",
                    np.isclose(
                        video_to_timestamp - video_from_timestamp,
                        metadata_length / metadata_fps,
                        rtol=0.0,
                        atol=timestamp_tolerance_s,
                    ),
                    f"episode {episode_index} video interval matches its length",
                    f"episode {episode_index} video interval does not match its length",
                )
            )
        checks.extend(episode_checks)
        episodes.append(
            EpisodeSummary(
                episode_index=int(episode_index),
                length=metadata_length,
                duration_s=float(len(episode_timestamps) / metadata_fps),
                mean_frame_period_s=float(frame_periods.mean()) if len(frame_periods) else 0.0,
                video_from_timestamp=video_from_timestamp,
                video_to_timestamp=video_to_timestamp,
            )
        )

    if sample_loader is None:
        raise InspectionError("a LeRobot sample loader is required")
    sample = sample_loader(root)
    reported_sample_keys = ("action", "observation.state", *camera_features)
    sample_shapes = {key: _shape(sample[key]) for key in reported_sample_keys}
    expected_camera_shapes = {
        key: (
            feature_shapes[key][2],
            feature_shapes[key][0],
            feature_shapes[key][1],
        )
        for key in camera_features
    }
    expected_sample_shapes = {
        "action": (6,),
        "observation.state": (6,),
        **expected_camera_shapes,
    }
    checks.append(
        _result(
            "decoded_sample_shapes",
            sample_shapes == expected_sample_shapes,
            "decoded sample shapes match dataset features",
            f"decoded sample shapes {sample_shapes} do not match {expected_sample_shapes}",
        )
    )

    return InspectionReport(
        root=root,
        robot_type=str(info["robot_type"]),
        task=str(tasks["task"][0]),
        fps=float(info["fps"]),
        total_episodes=int(info["total_episodes"]),
        total_frames=int(info["total_frames"]),
        feature_shapes=feature_shapes,
        camera_features=camera_features,
        episodes=tuple(episodes),
        sample_shapes=sample_shapes,
        checks=tuple(checks),
    )
