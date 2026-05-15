import subprocess
from pathlib import Path
from typing import IO

from .models import RsyncLocation

# TODO: INCLUDE_FILE could be an overall configuration parameter
INCLUDE_FILE = Path(__file__).parent / "includes.txt"


class RsyncClient:
    def __init__(self, executable: str = "rsync"):
        self.executable = executable

    def get_chunks(self, input: IO):
        # read newline or carriage return as chunk
        chunk = ""
        while char := input.read(1).decode("utf-8"):
            if char == "\n":
                yield chunk
                chunk = ""
            elif char == "\r":
                yield chunk
                chunk = char
            else:
                chunk += char

    def start_rsync(
        self,
        src: RsyncLocation,
        dest: RsyncLocation,
        contents_only: bool = False,
        dry_run: bool = False,
    ):
        rsync_cmd = self.generate_command(src, dest, contents_only=contents_only, dry_run=dry_run)
        rsync_proc = subprocess.Popen(
            rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, text=False
        )

        assert rsync_proc.stdout is not None

        try:
            yield from self.get_chunks(rsync_proc.stdout)

        finally:
            res = rsync_proc.wait()
            if res != 0:
                raise RuntimeError(f"rsync failed with exit code {res}")

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
            f"--include-from={INCLUDE_FILE}",
            "--exclude=*",
            "--rsync-path=sudo -n rsync",
        ]
        if dry_run:
            rsync_cmd.append("--dry-run")
            rsync_cmd.append("-v")
            rsync_cmd.append("--itemize-changes")
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
