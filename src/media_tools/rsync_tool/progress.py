import re

from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from .models import TransferDirection

# TODO: add console


# TODO: add separate column for xfr progress numbers
# TODO: render your own time remaining col from parsed?
class SpeedColumn(ProgressColumn):
    """Renders the upload speed from FFmpeg"""

    def render(self, task: Task) -> Text:
        speed = task.fields.get("speed", "00.00 kB/s")
        return Text(f"{speed}", style="green")


class RsyncProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.visible:
                yield Text.from_markup(str(task.description), style="bold green")

        yield self.make_tasks_table(self.tasks)


class RsyncProgressTracker:
    progress_pattern = re.compile(r"^\r\s+(\d+.\d+[KMGB])\s+(\d+)%\s+(.*/s)\s+(\d+:\d+:\d+)\s+$")
    progress_with_chk_pattern = re.compile(
        r"^\r\s+(\d+.\d+[KMGB])\s+(\d+)%\s+(.*/s)\s+(\d+:\d+:\d+)\s+\(xfr#(\d+), to-chk=(\d+)/\d+\)$"
    )

    def __init__(
        self, title_name: str | None = None, direction: TransferDirection = "upload"
    ) -> None:
        self.direction: TransferDirection = direction
        self.initiated = False
        self.started = False
        self.stopped = False
        self.task_id = None
        self.finalizing = False
        self.initializing = False
        self.initialize_task_id = None
        self.finalize_task_id = None
        self.title_name = title_name

        self.transfer_progress = RsyncProgress(
            SpinnerColumn(),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            SpeedColumn(),
            TimeRemainingColumn(),
        )

        if self.title_name is None:
            self.description = "Syncing files with rsync"
        else:
            self.description = (
                f"{self.direction.capitalize()}ing [italic cyan]{self.title_name}[/italic cyan]"
            )

        self.initialize_progress = Progress(
            SpinnerColumn(), TextColumn("[bold green]{task.description}")
        )
        self.finalize_progress = Progress(
            SpinnerColumn(), TextColumn("[bold green]{task.description}")
        )

        group = Group(self.initialize_progress, self.transfer_progress, self.finalize_progress)

        self.live: Live = Live(group, refresh_per_second=10)

    def initialize(self):
        self.initializing = True
        if not self.live.is_started:
            self.live.start()
        self.initialize_task_id = self.initialize_progress.add_task(
            "Waiting for rsync progress...", total=None
        )

    def start_progress(self):
        self.started = True
        if not self.live.is_started:
            self.live.start()
        if self.initializing and self.initialize_task_id is not None:
            self.initialize_progress.update(self.initialize_task_id, visible=False)
            self.initialize_progress.remove_task(self.initialize_task_id)
            self.initialize_progress.stop()
        self.task_id = self.transfer_progress.add_task(self.description, total=100)

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
                description=f"[green]{self.description} ({transfer_number} complete, {remaining_transfers} remain)",
            )
            if remaining_transfers == 0:
                if not self.finalizing:
                    self.finalize_task_id = self.finalize_progress.add_task(
                        "[green]Finalizing transfer...", total=None
                    )
                    self.finalizing = True
