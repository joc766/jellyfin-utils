from collections import deque
from pathlib import Path

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config

from media_tools.ffmpeg_tool import FFmpegClient


def get_large_test_file():
    cache_dir = Path(".pytest_cache/large-files")
    cache_dir.mkdir(parents=True, exist_ok=True)

    local_file = cache_dir / "test-small-mkv.mkv"

    if not local_file.exists():
        s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        s3.download_file(
            Bucket="jellyfin-utils-sample-files-195008820293-us-east-1-an",
            Key="test-small-mkv.mkv",
            Filename=str(local_file),
        )

    return local_file


def test_ffprobe_duration():
    test_mkv = get_large_test_file()
    client = FFmpegClient(test_mkv, "DVD")
    correct_duration = 147.213733333
    returned_duration = client.get_ffprobe_duration()
    assert correct_duration == returned_duration


# This test may take a couple minutes
@pytest.mark.slow
def test_compress_mkv(tmp_path):
    test_mkv = get_large_test_file()
    output = tmp_path / "test-small-mkv.mkv"
    client = FFmpegClient(test_mkv, "DVD")
    deque(client.start_compress_mkv(output), maxlen=0)
