from rich.console import Console, Group
from rich.live import Live
from rich.markup import escape
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.status import Status
from rich.text import Text

from .models import RsyncState, TransferDirection


# TODO: render your own time remaining col from parsed?
class SpeedColumn(ProgressColumn):
    """Renders the upload speed from FFmpeg"""

    def render(self, task: Task) -> Text:
        speed = task.fields.get("speed", "00.00 kB/s")
        return Text(f"{speed}", style="yellow")


class RsyncProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.visible:
                yield Text.from_markup(str(task.description))

        yield self.make_tasks_table(self.tasks)


class RsyncRender:
    def __init__(self, title_name: str, direction: TransferDirection, console: Console):
        self.direction = direction
        self.title_name = title_name
        self.console = console

        bar_width = self.console.width if self.console.width < 80 else 80

        self.transfer_progress = RsyncProgress(
            BarColumn(bar_width=bar_width),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            SpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        )

        self.description = f"{self.direction.capitalize()}ing [italic cyan]'{escape(self.title_name)}'[/italic cyan]"
        self.status = Status("Initializing...", console=console)

        self.transfer_task_id = self.transfer_progress.add_task(
            self.description, start=False, visible=False
        )

        group = Group(self.status, self.transfer_progress)

        self._live: Live = Live(group, refresh_per_second=10, transient=True, console=console)

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()
        if exc_type is None:
            self.console.print(
                f"{self.direction.capitalize()} [italic cyan]'{escape(self.title_name)}'[/italic cyan] complete."
            )
        return False

    @property
    def transfer_task(self):
        return self.transfer_progress._tasks[self.transfer_task_id]

    def update(self, new_state: RsyncState):
        description = (
            self.description
            + f"[dim][{new_state.transfer_number}/{new_state.transfer_number + new_state.remaining_transfers}][/dim]"
            if new_state.transfer_number is not None and new_state.remaining_transfers is not None
            else self.description
        )

        if not self.transfer_task.started:
            self._live.update(Group(self.transfer_progress))
            self.transfer_progress.start_task(self.transfer_task_id)
            self.transfer_progress.update(self.transfer_task_id, visible=True)

        self.transfer_progress.update(
            self.transfer_task_id,
            description=description,
            completed=new_state.percent_completed,
            speed=new_state.speed,
        )

        if new_state.remaining_transfers == 0:
            self.status.update("Finalizing...")
            self.transfer_progress.stop_task(self.transfer_task_id)
            self.transfer_progress.update(self.transfer_task_id, visible=False)
            self._live.update(Group(self.status))
