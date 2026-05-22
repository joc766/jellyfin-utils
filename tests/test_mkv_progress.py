from pathlib import Path

from media_tools.makemkv_tool.progress import MakeMKVProgressTracker

DATA_DIR = Path(__file__).resolve().parent / "data"


def test_mkv_progress_info(testing_mode: bool = False):
    test_file = (DATA_DIR / "full-info-prog-output.txt").open(
        mode="r", buffering=1, encoding="utf-8"
    )
    parser = MakeMKVProgressTracker(test_file)
    parser.track_progress(testing_mode=testing_mode)


def test_mkv_progress_mkv(testing_mode: bool = False):
    test_file = (DATA_DIR / "full-mkv-prog-output.txt").open(
        mode="r", buffering=1, encoding="utf-8"
    )
    parser = MakeMKVProgressTracker(test_file)
    parser.track_progress(testing_mode=testing_mode)
