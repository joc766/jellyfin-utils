import re
from typing import IO

from .models import MakeMKVProgressState, ProgCurrEvent, ProgEvent, ProgTotalEvent, ProgValueEvent


class MakeMKVProgressTracker:
    PROG_TOTAL_PATTERN = re.compile('^PRGT:(\\d+),(\\d+),"([^"]+)"$')
    PROG_CURR_PATTERN = re.compile('^PRGC:(\\d+),(\\d+),"([^"]+)"$')
    PROG_VALUE_PATTERN = re.compile("^PRGV:(\\d+),(\\d+),(\\d+)$")
    PROG_TASK_COMPLETE_PATTERN = re.compile("^MSG:5011")

    # init method for when a stdout can be passed directly
    def __init__(self) -> None:
        self.state = MakeMKVProgressState(
            prog_total=None,
            prog_curr=None,
            total_size=65536,
            curr_size=65536,
            status="Preparing MakeMKV",
        )

    def track_progress(self, proc: IO, verbose: bool = False):
        for line in proc:
            if verbose:
                print(line)
            yield self.handle_line(line)

    def handle_line(self, line) -> MakeMKVProgressState:
        line = line.rstrip("\n")
        if line[0:5] in ("PRGT:", "PRGC:", "PRGV:"):
            event = self.parse_line(line)
            if event is not None:
                self.apply_progress(event)
        elif self.PROG_TASK_COMPLETE_PATTERN.match(line):
            self.complete_all()
        return self.state

    def update_status(self, status: str):
        self.state.status = status

    def complete_all(self):
        self.state.prog_total = None
        self.state.prog_curr = None

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
                self.state.prog_total = 0
                self.state.total_task_name = event.name
            case ProgCurrEvent():
                self.state.prog_curr = 0
                self.state.curr_task_name = event.name
            case ProgValueEvent():
                # update total progress
                self.state.prog_total = event.total
                self.state.prog_curr = event.current
                self.state.total_size = event.max
                self.state.curr_size = event.max
