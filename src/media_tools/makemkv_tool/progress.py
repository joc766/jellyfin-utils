import re
from time import sleep
from typing import IO

from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.status import Status

from .models import ProgCurrEvent, ProgEvent, ProgTotalEvent, ProgValueEvent


class MakeMKVProgressTracker:
    PROG_TOTAL_PATTERN = re.compile('^PRGT:(\\d+),(\\d+),"([^"]+)"$')
    PROG_CURR_PATTERN = re.compile('^PRGC:(\\d+),(\\d+),"([^"]+)"$')
    PROG_VALUE_PATTERN = re.compile("^PRGV:(\\d+),(\\d+),(\\d+)$")
    PROG_TASK_COMPLETE_PATTERN = re.compile("^MSG:5011")

    # init method for when a stdout can be passed directly
    def __init__(self, proc: IO | None = None, console: Console | None = None) -> None:
        self.proc = proc
        self.started = False
        self.finished = False
        self.console = console

        self.status = Status("[bold white]Running MakeMKVCon", console=self.console)

        self.progress = Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>5.1f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        self._live: Live = Live(
            self.render(), refresh_per_second=10, console=self.console, transient=True
        )

        self.total_task_id: TaskID | None = None
        self.curr_task_id: TaskID | None = None

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove_completed_tasks()
        self.status.stop()
        self.progress.stop()
        self._live.stop()
        if self.console is not None and exc_type is None:
            self.console.print("[bold white]MakeMKV Complete.[/bold white]")
        return False

    def render(self):
        return Group(self.status, self.progress)

    def suspend(self):
        self._live.stop()

    def resume(self):
        self._live = Live(
            self.render(), refresh_per_second=10, console=self.console, transient=True
        )
        self._live.start()

    def set_status(self, status: str):
        self.status.update(status)
        self._live.update(self.render(), refresh=True)

    def remove_completed_tasks(self):
        for task in self.progress.tasks:
            if task.finished:
                self.progress.remove_task(task.id)

    def complete_all(self):
        if self.total_task_id is not None:
            self.progress.update(self.total_task_id, completed=65536)
        if self.curr_task_id is not None:
            self.progress.update(self.curr_task_id, completed=65536)

    def track_progress(self, verbose=False, testing_mode=False):
        if self.proc is None:
            raise Exception("track_progress cannot be called when proc is not provided.")
        for line in self.proc:
            if verbose:
                print(line)
            self.handle_line(line)
            if testing_mode:
                sleep(0.001)

    def handle_line(self, line) -> None:
        line = line.rstrip("\n")
        if line[0:5] in ("PRGT:", "PRGC:", "PRGV:"):
            event = self.parse_line(line)
            if event is not None:
                self.apply_progress(event)
        elif self.PROG_TASK_COMPLETE_PATTERN.match(line):
            self.complete_all()

    def parse_line(self, line: str) -> ProgEvent | None:
        if prog_total_match := self.PROG_TOTAL_PATTERN.match(line):
            prog_total_event = ProgTotalEvent(
                code=prog_total_match.group(1),
                name=prog_total_match.group(3),
                raw_line=line,
            )
            return prog_total_event
        elif prog_curr_match := self.PROG_CURR_PATTERN.match(line):
            prog_curr_event = ProgCurrEvent(
                code=prog_curr_match.group(1),
                name=prog_curr_match.group(3),
                raw_line=line,
            )
            return prog_curr_event
        elif prog_value_match := self.PROG_VALUE_PATTERN.match(line):
            prog_value_event = ProgValueEvent(
                current=int(prog_value_match.group(1)),
                total=int(prog_value_match.group(2)),
                max=int(prog_value_match.group(3)),
                raw_line=line,
            )
            return prog_value_event

    def apply_progress(self, event: ProgEvent):
        match event:
            case ProgTotalEvent():
                # update total task
                if self.total_task_id is not None:
                    self.progress.reset(
                        self.total_task_id,
                        description=f"[green]{event.name}",
                        completed=0,
                        total=65536,
                        start=True,
                    )
                else:
                    self.total_task_id = self.progress.add_task(f"[green]{event.name}", total=65536)
            case ProgCurrEvent():
                # complete and hide previous curr_task if exists and is new
                if self.curr_task_id is not None:
                    self.progress.reset(
                        self.curr_task_id,
                        description=f"[blue]{event.name}",
                        completed=0,
                        total=65536,
                        start=True,
                    )
                else:
                    self.curr_task_id = self.progress.add_task(
                        f"[blue]{event.name}", total=65536, start=True
                    )
            case ProgValueEvent():
                # update total progress
                if self.total_task_id is not None:
                    self.progress.update(self.total_task_id, completed=event.total)
                if self.curr_task_id is not None:
                    self.progress.update(self.curr_task_id, completed=event.current)
