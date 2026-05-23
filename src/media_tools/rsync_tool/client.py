import re
import subprocess
from collections import defaultdict
from collections.abc import Generator
from pathlib import Path
from typing import IO

from rich.console import Console

from .models import (
    ContentFormat,
    ContentType,
    RsyncChangeInfo,
    RsyncLocation,
    RsyncSources,
    TransferDirection,
)


class RsyncClient:
    INTRO_MSG_PATTERN = re.compile(r"^sending incremental file list$")
    SENT_MSG_PATTERN = re.compile(r"^sent .* bytes  received .* bytes .* bytes/sec$")
    TOTAL_MSG_PATTERN = re.compile(r"^total size is .*  speedup is.*")
    ITEMIZED_PATTERN = re.compile(r"^(?P<prefix>.{11})\s+(?P<size>\d+\.\d+[KMGB])\s+(?P<path>.+)$")

    CHANGES = {
        "s": "size",
        "t": "timestamp",
        "c": "checksum",
        "p": "permissions",
        "o": "owner",
        "g": "group",
    }

    def __init__(
        self,
        *,
        jellyfin_base: Path,
        jellyfin_host: str,
        jellyfin_user: str,
        local_base: Path,
        console: Console,
        direction: TransferDirection,
        content_format: ContentFormat,
        content_type: ContentType,
        executable: str = "rsync",
    ):
        self.executable = executable
        self.direction: TransferDirection = direction
        self.content_format: ContentFormat = content_format
        self.content_type: ContentType = content_type
        self.console: Console = console
        self.jellyfin_base: Path = jellyfin_base
        self.jellyfin_host: str = jellyfin_host
        self.jellyfin_user: str = jellyfin_user
        self.local_base: Path = local_base

    @classmethod
    def from_config(
        cls,
        config,
        *,
        console: Console,
        direction: TransferDirection,
        content_format: ContentFormat,
        content_type: ContentType,
    ):
        return cls(
            jellyfin_base=config.jellyfin_base,
            jellyfin_host=config.jellyfin_host,
            jellyfin_user=config.jellyfin_user,
            local_base=config.local_base,
            console=console,
            direction=direction,
            content_format=content_format,
            content_type=content_type,
        )

    @property
    def src(self):
        return self._get_src_and_dest().src

    @property
    def dest(self):
        return self._get_src_and_dest().dest

    def _get_src_and_dest(self) -> RsyncSources:
        src_base = self.local_base if self.direction == "upload" else self.jellyfin_base
        src_path = src_base / self.content_format / self.content_type
        src_host = None if self.direction == "upload" else self.jellyfin_host
        src_user = None if self.direction == "upload" else self.jellyfin_user
        src = RsyncLocation(src_path, host=src_host, user=src_user)

        dest_base = self.jellyfin_base if self.direction == "upload" else self.local_base
        dest_path = dest_base / self.content_format / self.content_type
        dest_host = self.jellyfin_host if self.direction == "upload" else None
        dest_user = self.jellyfin_user if self.direction == "upload" else None
        dest = RsyncLocation(dest_path, host=dest_host, user=dest_user)

        return RsyncSources(src, dest)

    def _get_chunks(self, input: IO, debug: bool = False) -> Generator[str, None, None]:
        # read newline or carriage return as chunk
        chunk = ""
        while char := input.read(1).decode("utf-8"):
            if char == "\n":
                if debug:
                    self.console.print(chunk)
                yield chunk
                chunk = ""
            elif char == "\r":
                if debug:
                    self.console.print(chunk)
                yield chunk
                chunk = char
            else:
                chunk += char

    def _sync(
        self,
        subdir: str | None = None,
        contents_only: bool = False,
        dry_run: bool = False,
        debug: bool = False,
    ) -> Generator[str, None, None]:

        src_root, dest = self._get_src_and_dest()
        if subdir is None:
            src = src_root
        else:
            src = RsyncLocation(src_root.path / subdir, host=src_root.host, user=src_root.user)

        rsync_cmd = self.generate_command(src, dest, contents_only=contents_only, dry_run=dry_run)
        rsync_proc = subprocess.Popen(
            rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, text=False
        )

        assert rsync_proc.stdout is not None

        try:
            yield from self._get_chunks(rsync_proc.stdout, debug=debug)

        finally:
            res = rsync_proc.wait()
            if res != 0:
                raise RuntimeError(f"rsync failed with exit code {res}")

    def sync(self, dry_run: bool = False, debug: bool = False):
        """Sync the contents of root local_base with jellyfin_base"""
        return self._sync(contents_only=True, dry_run=dry_run, debug=debug)

    def sync_subdir(self, subdir: str, dry_run: bool = False, debug: bool = False):
        """Sync a subdirectory of local_base to jellyfin_base"""
        return self._sync(subdir=subdir, contents_only=False, dry_run=dry_run, debug=debug)

    def generate_command(
        self,
        src: RsyncLocation,
        dest: RsyncLocation,
        contents_only: bool = False,
        dry_run: bool = False,
    ) -> list[str]:
        rsync_cmd = [
            "rsync",
            "-rth",
            "--rsync-path=sudo -n rsync",
        ]
        # filter rules
        rsync_cmd.extend(
            [
                "-f",
                "+ *.mkv",
                "-f",
                "+ *.mp4",
                "-f",
                "+ *.mov",
                "-f",
                "+ */",
                "-f",
                "- *",
            ]
        )
        if dry_run:
            rsync_cmd.append("--dry-run")
            rsync_cmd.append("-v")
            rsync_cmd.append("--itemize-changes")
            rsync_cmd.append("--out-format=%i %'''l %n")
        else:
            rsync_cmd.append("--info=progress2")
            rsync_cmd.append("--chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r")
            rsync_cmd.append("--partial")
            rsync_cmd.append("--no-i-r")

        if contents_only and not str(src).endswith("/"):
            rsync_cmd.append(f"{src.render()}/")
        else:
            rsync_cmd.append(src.render())

        rsync_cmd.append(dest.render())

        return rsync_cmd

    def get_new_files(self, debug: bool = False) -> dict[str, dict[str, RsyncChangeInfo]]:
        """Get the list of files in local_base not in jellyfin_base using sync(dry_run=True)"""
        content_to_sync = defaultdict(dict[str, RsyncChangeInfo])
        for line in self.sync(dry_run=True, debug=debug):
            if (
                not self.INTRO_MSG_PATTERN.match(line)
                and not self.SENT_MSG_PATTERN.match(line)
                and not self.TOTAL_MSG_PATTERN.match(line)
            ):
                if item_match := self.ITEMIZED_PATTERN.match(line):
                    prefix = item_match["prefix"]
                    itemized_changes = {
                        "raw_prefix": prefix,
                        "update": prefix[0],
                        "filetype": prefix[1],
                        "changes_raw": prefix[2:],
                        "path": Path(item_match["path"]),
                        "is_created": prefix[2:] == "+++++++++",
                        "changes": dict(zip("cstpoguax", prefix[2:], strict=False)),
                    }
                    path = itemized_changes["path"]
                    if len(str(path).split("/")) != 2:
                        pass
                        # print(f"ignoring {line}")
                    else:
                        if itemized_changes["filetype"] == "f":
                            size = item_match["size"]
                            movie_title = str(path.parent)
                            filename = path.name
                            change_info = RsyncChangeInfo()
                            change_info.size = size
                            change_info.description = (
                                "New"
                                if itemized_changes["is_created"]
                                else ",".join(
                                    self.CHANGES[x]
                                    for x in itemized_changes["changes"].values()
                                    if x != "."
                                )
                            )
                            content_to_sync[movie_title][filename] = change_info

        return content_to_sync
