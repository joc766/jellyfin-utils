import re
from collections.abc import Iterable

from .models import RsyncState, TransferDirection


class RsyncProgressTracker:
    progress_pattern = re.compile(r"^\r\s+(\d+.\d+[KMGB])\s+(\d+)%\s+(.*/s)\s+(\d+:\d+:\d+)\s+$")
    progress_with_chk_pattern = re.compile(
        r"^\r\s+(\d+.\d+[KMGB])\s+(\d+)%\s+(.*/s)\s+(\d+:\d+:\d+)\s+\(xfr#(\d+), to-chk=(\d+)/(\d+)\)$"
    )

    def __init__(
        self, title_name: str | None = None, direction: TransferDirection = "upload"
    ) -> None:
        self.direction: TransferDirection = direction
        self.title_name = title_name
        self.state = RsyncState()
        # TODO: maybe use a dry run to get the total transfer size ahead of time.
        #

    def track(self, proc: Iterable[str], verbose: bool = False):
        for line in proc:
            if verbose:
                print(line)
            yield self.handle_line(line)

    def handle_line(self, line: str):
        if progress_match := self.progress_pattern.match(line):
            self.state.total_transferred = progress_match.group(1)
            self.state.percent_completed = float(progress_match.group(2))
            self.state.speed = progress_match.group(3)
            self.state.time_remaining = progress_match.group(4)

        elif progress_with_chk_match := self.progress_with_chk_pattern.match(line):
            self.state.total_transferred = progress_with_chk_match.group(1)
            self.state.percent_completed = float(progress_with_chk_match.group(2))
            self.state.speed = progress_with_chk_match.group(3)
            self.state.time_remaining = progress_with_chk_match.group(4)
            self.state.transfer_number = int(progress_with_chk_match.group(5))
            self.state.remaining_transfers = int(progress_with_chk_match.group(6))

        return self.state
