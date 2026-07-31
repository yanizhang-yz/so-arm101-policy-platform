from pathlib import Path
from types import SimpleNamespace

from lerobot.datasets.dataset_writer import DatasetWriter

from scripts.record_dataset import clear_episode_buffer_with_video_cleanup


def make_writer(root: Path) -> DatasetWriter:
    meta = SimpleNamespace(
        total_episodes=7,
        features={
            "episode_index": {"dtype": "int64"},
            "observation.images.still": {"dtype": "image"},
            "observation.images.front": {"dtype": "video"},
        },
        image_keys=["observation.images.still"],
        video_keys=["observation.images.front"],
        depth_keys=["observation.images.front"],
    )
    return DatasetWriter(
        meta=meta,
        root=root,
        rgb_encoder=None,
        depth_encoder=None,
        encoder_threads=None,
        batch_encoding_size=1,
    )


def test_cleanup_removes_image_and_video_temp_directories(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    image_dir = writer._get_image_file_dir(7, "observation.images.still")
    video_dir = writer._get_image_file_dir(7, "observation.images.front")
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
    assert writer.episode_buffer["episode_index"] == 7
