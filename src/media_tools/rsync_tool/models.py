from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple


class RsyncChangeInfo:
    description: str
    size: str


@dataclass
class RsyncLocation:
    path: Path
    host: str | None = None
    user: str | None = None

    def render(self) -> str:
        path = str(self.path)

        if self.host is None:
            return str(self.path)

        prefix = f"{self.user}@{self.host}" if self.user else self.host

        return f"{prefix}:{path}"


@dataclass
class RsyncState:
    total_transferred: str = ""
    percent_completed: float = 0.0
    speed: str = ""
    time_remaining: str = ""
    transfer_number: int | None = None
    remaining_transfers: int | None = None


class RsyncSources(NamedTuple):
    src: RsyncLocation
    dest: RsyncLocation


TransferDirection = Literal["upload", "download"]
ContentFormat = Literal["raw", "compressed"]
ContentType = Literal["movie", "show"]
