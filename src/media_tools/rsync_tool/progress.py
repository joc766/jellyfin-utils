import re

from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

# TODO: add console


# TODO: add separate column for xfr progress numbers
# TODO: render your own time remaining col from parsed?
class SpeedColumn(ProgressColumn):
    """Renders the upload speed from FFmpeg"""

    def render(self, task: Task) -> Text:
        speed = task.fields.get("speed", "00.00 kB/s")
        return Text(f"{speed}", style="green")


class RsyncProgressTracker:
    progress_pattern = re.compile(r"^\r\s+(\d+.\d+[KMGB])\s+(\d+)%\s+(.*/s)\s+(\d+:\d+:\d+)\s+$")
    progress_with_chk_pattern = re.compile(
        r"^\r\s+(\d+.\d+[KMGB])\s+(\d+)%\s+(.*/s)\s+(\d+:\d+:\d+)\s+\(xfr#(\d+), to-chk=(\d+)/\d+\)$"
    )

    def __init__(self, title_name: str | None = None) -> None:
        self.started = False
        self.stopped = False
        self.task_id = None
        self.finalizing = False
        self.finalize_task_id = None
        self.title_name = title_name

        self.transfer_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:5.1f}%"),
            TimeElapsedColumn(),
            SpeedColumn(),
            TimeRemainingColumn(),
        )

        if self.title_name is None:
            self.description = "Syncing files with rsync"
        else:
            year = None
            if year_match := re.search(r"(\(.*\))", self.title_name):
                year = year_match.group(1)
            self.description = (
                f"Syncing {self.title_name[:10]}...{year if year is not None else ''}"
            )

        self.finalize_progress = Progress(SpinnerColumn(), TextColumn("[bold]{task.description}"))

        group = Group(self.transfer_progress, self.finalize_progress)

        self.live = Live(group, refresh_per_second=10)

    def start_progress(self):
        self.started = True
        self.live.start()
        self.task_id = self.transfer_progress.add_task(f"[green]{self.description}", total=100)

    def stop_progress(self):
        self.stopped = True
        if self.finalize_task_id is not None:
            self.finalize_progress.update(
                self.finalize_task_id,
                description="[green]Finalizing transfer... done.",
                completed=1,
                total=1,
                visible=False,
            )
        self.transfer_progress.stop()
        self.finalize_progress.stop()
        self.live.stop()

    def handle_line(self, line: str):
        if progress_match := self.progress_pattern.match(line):
            total_transferred = progress_match.group(1)
            percent_completed = float(progress_match.group(2))
            speed = progress_match.group(3)
            time_remaining = progress_match.group(4)

            if not self.started:
                self.start_progress()
            assert self.task_id is not None
            # TODO: maybe use a dry run to get the total transfer size ahead of time.
            self.transfer_progress.update(self.task_id, completed=percent_completed, speed=speed)

        elif progress_with_chk_match := self.progress_with_chk_pattern.match(line):
            total_transferred = progress_with_chk_match.group(1)
            percent_completed = float(progress_with_chk_match.group(2))
            speed = progress_with_chk_match.group(3)
            time_remaining = progress_with_chk_match.group(4)
            transfer_number = int(progress_with_chk_match.group(5))
            remaining_transfers = int(progress_with_chk_match.group(6))

            assert self.task_id is not None

            self.transfer_progress.update(
                self.task_id,
                completed=percent_completed,
                description=f"[green]Syncing {self.description} ({transfer_number} complete, {remaining_transfers} remain)",
            )
            if remaining_transfers == 0:
                if not self.finalizing:
                    self.finalize_task_id = self.finalize_progress.add_task(
                        "[green]Finalizing transfer...", total=None
                    )
                    self.finalizing = True
