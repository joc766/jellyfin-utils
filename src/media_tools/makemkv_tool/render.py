from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.status import Status
from rich.text import Text

from .models import MakeMKVProgressState


class MakeMKVProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.visible:
                yield Text.from_markup(f"{task.description}")

        yield self.make_tasks_table(self.tasks)


class MakeMKVProgressRenderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.started = False
        self.finished = False
        self.status = Status("[bold]Running MakeMKVCon", console=self.console)

        bar_width = self.console.width if self.console.width < 80 else 80
        self.total_progress = MakeMKVProgress(
            BarColumn(complete_style="magenta", finished_style="green", bar_width=bar_width),
            TextColumn("{task.percentage:>5.1f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.curr_progress = MakeMKVProgress(
            BarColumn(complete_style="cyan", finished_style="green", bar_width=bar_width),
            TextColumn("{task.percentage:>5.1f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        self._live: Live = Live(
            self.render(), refresh_per_second=10, console=self.console, transient=True
        )

        self.total_task_id: TaskID = self.total_progress.add_task("Total", start=False)
        self.curr_task_id: TaskID = self.curr_progress.add_task("Current", start=False)

    @property
    def total_task(self) -> Task:
        return self.total_progress._tasks[self.total_task_id]

    @property
    def curr_task(self) -> Task:
        return self.curr_progress._tasks[self.curr_task_id]

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()
        if exc_type is None:
            self.console.print("[bold white]MakeMKV Complete.[/bold white]")
        return False

    def render(self):
        return Group(self.status, self.total_progress, self.curr_progress)

    def update(self, new_state: MakeMKVProgressState):
        if new_state.prog_total is not None:
            if not self.total_task.started:
                self.total_progress.start_task(self.total_task_id)

            self.total_progress.update(
                self.total_task_id,
                description=new_state.total_task_name,
                total=new_state.total_size,
                completed=new_state.prog_total,
                visible=True,
            )  # optionally could force refresh
        else:
            if self.total_task.start_time is not None:
                self.total_progress.reset(self.total_task_id, start=False, visible=False)
                self.total_progress.stop_task(self.total_task_id)

        if new_state.prog_curr is not None:
            if not self.curr_task.started:
                self.curr_progress.start_task(self.curr_task_id)
            self.curr_progress.update(
                self.curr_task_id,
                description=new_state.curr_task_name,
                total=new_state.curr_size,
                completed=new_state.prog_curr,
                visible=True,
            )
        else:
            if self.curr_task.start_time is not None:
                self.curr_progress.reset(self.curr_task_id, start=False, visible=False)
                self.curr_progress.stop_task(self.curr_task_id)

        self.update_status(new_state.status)

    def update_status(self, status: str):
        if str(self.status.status) != status:
            self.status.update(Text.from_markup(f"[bold]{status}"))

    def suspend(self):
        self._live.stop()

    def resume(self):
        self._live = Live(
            self.render(), refresh_per_second=10, console=self.console, transient=True
        )
        self._live.start()
