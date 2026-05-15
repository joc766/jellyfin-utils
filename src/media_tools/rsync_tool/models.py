from dataclasses import dataclass
from pathlib import Path
from typing import Literal


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


TransferDirection = Literal["upload", "download"]
ContentFormat = Literal["raw", "compressed"]
ContentType = Literal["movie", "show"]
