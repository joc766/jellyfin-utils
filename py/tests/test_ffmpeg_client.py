from collections import deque
from pathlib import Path

import pytest

from media_tools.ffmpeg_tool import FFmpegClient

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_ffprobe_duration():
    test_mkv = DATA_DIR / "test-small-mkv.mkv"
    client = FFmpegClient(test_mkv, "DVD")
    correct_duration = 146.212733333
    returned_duration = client.get_ffprobe_duration()
    assert correct_duration == returned_duration


# This test may take a couple minutes
@pytest.mark.slow
def test_compress_mkv(tmp_path):
    test_mkv = DATA_DIR / "test-small-mkv.mkv"
    output = tmp_path / "test-small-mkv.mkv"
    client = FFmpegClient(test_mkv, "DVD")
    deque(client.start_compress_mkv(output), maxlen=0)
