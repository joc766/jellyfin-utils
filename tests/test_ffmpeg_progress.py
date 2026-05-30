from pathlib import Path
from time import sleep

from media_tools.ffmpeg_tool.progress import FFmpegProgressRender, FFmpegProgressTracker

DATA_DIR = Path(__file__).parent / "data"


def test_ffmpeg_progress(testing_mode: bool = False, verbose: bool = False):
    test_file = (DATA_DIR / "ffmpeg-output.txt").open(mode="r", buffering=1, encoding="utf-8")
    duration = 1280.672
    tracker = FFmpegProgressTracker()
    with FFmpegProgressRender(duration) as render:
        for curr_state in tracker.track_progress(test_file, verbose=verbose):
            render.update(curr_state)
            if testing_mode:
                sleep(0.001)
