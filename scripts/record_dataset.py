"""Run LeRobot recording with reliable rejected-episode video cleanup."""

from __future__ import annotations

import shutil

import numpy as np
from lerobot.datasets.dataset_writer import DatasetWriter
from lerobot.scripts import lerobot_record


UPSTREAM_CLEAR_EPISODE_BUFFER = DatasetWriter.clear_episode_buffer


def _normalize_episode_index(value: int | np.ndarray) -> int:
    if isinstance(value, np.ndarray):
        value = value.item() if value.size == 1 else value[0]
    return int(value)


def clear_episode_buffer_with_video_cleanup(
    writer: DatasetWriter,
    delete_images: bool = True,
) -> None:
    """Delete rejected video frames, then delegate buffer cleanup to LeRobot."""
    if delete_images:
        writer._wait_image_writer()
        episode_index = _normalize_episode_index(writer.episode_buffer["episode_index"])
        image_keys = set(writer._meta.image_keys)
        extra_camera_keys = dict.fromkeys(
            [*writer._meta.video_keys, *writer._meta.depth_keys]
        )

        for camera_key in extra_camera_keys:
            if camera_key in image_keys:
                continue
            frame_dir = writer._get_image_file_dir(episode_index, camera_key)
            if frame_dir.is_dir():
                shutil.rmtree(frame_dir)

    UPSTREAM_CLEAR_EPISODE_BUFFER(writer, delete_images)


def install_safe_rerecord_patch() -> None:
    """Install the cleanup patch once for this recording process."""
    if DatasetWriter.clear_episode_buffer is clear_episode_buffer_with_video_cleanup:
        return
    DatasetWriter.clear_episode_buffer = clear_episode_buffer_with_video_cleanup


def main() -> int | None:
    install_safe_rerecord_patch()
    return lerobot_record.main()


if __name__ == "__main__":
    raise SystemExit(main())
