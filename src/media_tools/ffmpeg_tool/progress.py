import re
from collections.abc import Iterable
from dataclasses import dataclass

from rich.console import Console
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


@dataclass
class FFmpegProgressState:
    out_time: int
    out_time_seconds: float
    speed: str


class SpeedColumn(ProgressColumn):
    """Renders the upload speed from FFmpeg"""

    def render(self, task: Task) -> Text:
        speed = task.fields.get("speed", 0.0)
        return Text(f"{speed}", style="green")


class FFmpegProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.visible:
                yield Text.from_markup(f"[bold]{task.description}")

        yield self.make_tasks_table(self.tasks)


class FFmpegProgressRender:
    def __init__(self, duration: float, console: Console | None = None):
        """duration: duration in seconds"""
        self.console = console or Console()
        self.duration = duration
        bar_width = self.console.width if self.console.width < 80 else 80
        self.progress = FFmpegProgress(
            BarColumn(bar_width=bar_width),
            TextColumn("{task.percentage:5.1f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            SpeedColumn(),
            transient=True,
        )
        self.task_id = self.progress.add_task(
            "Running ffmpeg compression", total=self.duration, start=False, visible=False
        )

    def __enter__(self):
        self.progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
        if exc_type is None:
            self.console.print("FFmpeg Complete.")
        return False

    @property
    def task(self):
        return self.progress._tasks[self.task_id]

    def update(self, new_state: FFmpegProgressState):
        if not self.task.started:
            self.progress.start_task(self.task_id)
            self.progress.update(
                self.task_id,
                visible=True,
                completed=new_state.out_time_seconds,
                speed=new_state.speed,
            )
        else:
            self.progress.update(
                self.task_id, completed=new_state.out_time_seconds, speed=new_state.speed
            )


class FFmpegProgressTracker:
    out_time_pattern = re.compile("^out_time_us=(\\d+)$")
    speed_pattern = re.compile("^speed=(\\d+\\.\\d+x)$")

    def __init__(self):
        self.started = False
        self.stopped = False
        self.state = FFmpegProgressState(out_time=0, out_time_seconds=0, speed="")

    def track_progress(self, proc: Iterable[str], verbose: bool = False):
        for line in proc:
            if verbose:
                print(line)
            yield self.handle_line(line)

    def handle_line(self, line: str):
        line = line.rstrip("\n")

        if out_time_match := self.out_time_pattern.match(line):
            out_time = int(out_time_match.group(1))
            out_time_seconds = out_time / 1_000_000
            self.state.out_time = out_time
            self.state.out_time_seconds = out_time_seconds
        elif speed_match := self.speed_pattern.match(line):
            speed = speed_match.group(1)
            self.state.speed = speed

        return self.state
