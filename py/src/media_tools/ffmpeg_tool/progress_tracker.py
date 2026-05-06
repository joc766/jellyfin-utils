import re

from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text


class SpeedColumn(ProgressColumn):
    """Renders the upload speed from FFmpeg"""

    def render(self, task: Task) -> Text:
        speed = task.fields.get("speed", 0.0)
        return Text(f"{speed}", style="green")


class FFmpegProgressTracker:
    out_time_pattern = re.compile("^out_time_us=(\\d+)$")
    speed_pattern = re.compile("^speed=(\\d+\\.\\d+x)$")

    def __init__(self, title_duration: float):
        """duration: duration in seconds"""
        self.started = False
        self.stopped = False
        self.duration = title_duration
        self.task_id = None

        self.progress = Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:5.1f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            SpeedColumn(),
        )

    def start_progress(self):
        self.started = True
        self.progress.start()
        self.task_id = self.progress.add_task(
            "[green]Running ffmpeg compression", total=self.duration
        )

    def stop_progress(self):
        self.stopped = True
        self.progress.stop()

    # TODO: add a track_progress function to handle each line?

    def handle_line(self, line: str):
        if not self.started:
            self.start_progress()
        line = line.rstrip("\n")

        assert self.task_id is not None

        if out_time_match := self.out_time_pattern.match(line):
            out_time = int(out_time_match.group(1))
            out_time_seconds = out_time / 1_000_000
            self.progress.update(self.task_id, completed=out_time_seconds)
        elif speed_match := self.speed_pattern.match(line):
            speed = speed_match.group(1)
            self.progress.update(self.task_id, speed=speed)
