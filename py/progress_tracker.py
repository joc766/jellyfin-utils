import re

from time import sleep

from dataclasses import dataclass
from typing import IO
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskID,
)


@dataclass
class ProgEvent:
    raw_line: str


@dataclass
class ProgTotalEvent(ProgEvent):
    code: str
    name: str


@dataclass
class ProgCurrEvent(ProgEvent):
    code: str
    name: str


@dataclass
class ProgValueEvent(ProgEvent):
    current: int
    total: int
    max: int


class MakeMKVProgressTracker:
    PROG_TOTAL_PATTERN = re.compile('^PRGT:(\\d+),(\\d+),"([^"]+)"$')
    PROG_CURR_PATTERN = re.compile('^PRGC:(\\d+),(\\d+),"([^"]+)"$')
    PROG_VALUE_PATTERN = re.compile("^PRGV:(\\d+),(\\d+),(\\d+)$")
    PROG_TASK_COMPLETE_PATTERN = re.compile("^MSG:5011")

    # init method for when a stdout can be passed directly
    def __init__(self, proc: IO | None = None) -> None:
        self.proc = proc

        self.progress = Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>5.1f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )

        self.total_task_queue: list[TaskID] = []
        self.curr_task_queue: list[TaskID] = []

        self.progress.start()

    def stop_progress(self):
        self.progress.stop()

    def track_progress(self, verbose=False, testing_mode=False):
        if self.proc is None:
            raise Exception(
                "track_progress cannot be called when proc is not provided."
            )
        try:
            for line in self.proc:
                if verbose:
                    print(line)
                self.handle_line(line)
                if testing_mode:
                    sleep(0.1)

        finally:
            self.progress.stop()

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
                # complete and hide previous total_task if exists
                if len(self.total_task_queue) > 0:
                    prev_task_id = self.total_task_queue.pop()
                    self.progress.update(prev_task_id, completed=65536, visible=False)
                # add new total_task
                self.total_task_queue.append(
                    self.progress.add_task(f"[green]{event.name}", total=65536)
                )
            case ProgCurrEvent():
                # complete and hide previous curr_task if exists
                if len(self.curr_task_queue) > 0:
                    prev_task_id = self.curr_task_queue.pop()
                    self.progress.update(prev_task_id, completed=65536, visible=False)
                # add new curr_task
                self.curr_task_queue.append(
                    self.progress.add_task(f"[blue]{event.name}", total=65536)
                )
            case ProgValueEvent():
                # update total progress
                if len(self.total_task_queue) > 0:
                    total_task_id = self.total_task_queue[0]
                    self.progress.update(total_task_id, completed=event.total)
                if len(self.curr_task_queue) > 0:
                    curr_task_id = self.curr_task_queue[0]
                    self.progress.update(curr_task_id, completed=event.current)

    def complete_all(self):
        if len(self.curr_task_queue) > 0:
            curr_task_id = self.curr_task_queue.pop()
            self.progress.update(curr_task_id, completed=65536, visible=False)
        if len(self.total_task_queue) > 0:
            total_task_id = self.total_task_queue.pop()
            self.progress.update(total_task_id, completed=65536, visible=False)
