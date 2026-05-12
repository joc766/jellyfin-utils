from pathlib import Path

from media_tools.ffmpeg_tool.progress import FFmpegProgressTracker

DATA_DIR = Path(__file__).parent / "data"


def test_ffmpeg_progress():
    test_file = (DATA_DIR / "ffmpeg-output.txt").open(mode="r", buffering=1, encoding="utf-8")
    duration = 1280.672
    tracker = FFmpegProgressTracker(duration)
    for line in test_file:
        tracker.handle_line(line)
