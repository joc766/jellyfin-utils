from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple

from media_tools.sftp_tool.client import JellyfinSFTPClient


class RsyncChangeInfo:
    description: str
    size: str

    def __repr__(self) -> str:
        return f"description: {self.description}, size: {self.size}"


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

    def mkdir(self):
        if self.host is None:
            self.path.mkdir(parents=True, exist_ok=True)
        else:
            # emulate mkdir -p behavior over sftp
            if self.user is None:
                raise ValueError("found empty user when connecting to remote jellyfin host")
            sftp_client = JellyfinSFTPClient(self.host, self.user, self.path).sftp_client
            dir_path = Path("")
            for folder in self.path.parts:
                dir_path = dir_path / folder
                try:
                    sftp_client.mkdir(str(dir_path))
                except OSError:
                    pass


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
