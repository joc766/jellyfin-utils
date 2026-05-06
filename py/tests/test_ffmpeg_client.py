from collections import deque
from pathlib import Path

import pytest

from media_tools.ffmpeg_tool import FFmpegClient

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_ffprobe_duration():
    test_mkv = DATA_DIR / "test-small-mkv.mkv"
    client = FFmpegClient(test_mkv, "DVD", output_dir=DATA_DIR)
    correct_duration = 796.862733333
    returned_duration = client.get_ffprobe_duration()
    assert correct_duration == returned_duration


# This test may take a couple minutes
@pytest.mark.slow
def test_compress_mkv():
    test_mkv = DATA_DIR / "test-small-mkv.mkv"
    client = FFmpegClient(test_mkv, "DVD", output_dir=DATA_DIR, overwrite=True)
    deque(client.start_compress_mkv(), maxlen=0)
    for file_path in DATA_DIR.glob("*.mp4"):
        if file_path.is_file():
            file_path.unlink()
