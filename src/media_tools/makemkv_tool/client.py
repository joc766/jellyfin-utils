import os
import shlex
import signal
import subprocess
from pathlib import Path

from rich.console import Console
from rich.text import Text

from media_tools.db.connection import complete_request, create_new_request

from .info_parser import MakeMKVInfoParser


# TODO: verify/add support for non-disk drives to allow testing with backed-up data
class MakeMKVClient:
    def __init__(self, *, output_base: Path, console: Console, executable: str = "makemkvcon"):
        self.executable: str = executable
        self.console = console
        self.drive_name = None
        self.disc_info = None
        self.output_base = output_base
        self.info_parser = MakeMKVInfoParser()

        if not self.output_base.exists():
            raise FileNotFoundError(f"Output base {self.output_base} does not exist.")

    def extract_drive_name(self):
        for line in self.get_info_lines():
            self.info_parser.handle_line(line)
            yield line

        drive_info = self.info_parser.extract_active_drive()

        if drive_info is not None:
            drive_name, _, _, _ = drive_info
        else:
            raise ValueError("Drive name not found")

        self.drive_name = drive_name

    def extract_disc_info(self):
        assert self.drive_name is not None

        for line in self.get_info_lines(self.drive_name):
            self.info_parser.handle_line(line)
            yield line
        disc_info = self.info_parser.build()

        self.disc_info = disc_info
        self.output_path = self.output_base / self.disc_info.disc_title

    def get_info_lines(self, drive_name: str = "disc:9999", cache_size: int = 16):
        info_proc = subprocess.Popen(
            [
                self.executable,
                "info",
                "-r",
                f"--cache={cache_size}",
                "--progress=-stdout",
                drive_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert info_proc.stdout is not None

        interrupted = False
        try:
            yield from info_proc.stdout
        except KeyboardInterrupt as e:
            info_proc.send_signal(signal.SIGINT)
            interrupted = True
            raise InterruptedError("MakeMKV Aborted!") from e
        finally:
            res = info_proc.wait()
            if res != 0 and not interrupted:
                raise RuntimeError(f"makemkvcon failed with exit code {res}")

    @property
    def cache_size(self) -> int | None:
        assert self.disc_info is not None
        assert hasattr(self.disc_info, "disc_type")
        return 512 if self.disc_info.disc_type == "DVD" else 1024

    def run_makemkv(self, title_id: int | None = None, debug: bool = False):
        assert self.disc_info is not None
        assert hasattr(self.disc_info, "disc_title")
        assert hasattr(self, "output_path")

        params_dict = {k: v for k, v in locals().items() if k != "self"}

        if not self.output_path.exists():
            self.output_path.mkdir()

        if self.console is not None and debug:
            self.console.print(str(self.output_path))

        if title_id is None:
            title = "all"
        else:
            title = str(title_id)
        mkv_command = [
            self.executable,
            "mkv",
            "-r",
            f"--cache={self.cache_size}",
            self.drive_name,
            title,
            str(self.output_path),
            "--progress=-stdout",
            "--messages=-same",
        ]

        mkv_command_str = shlex.join(mkv_command)

        if debug:
            self.console.print(Text("+ " + mkv_command_str))

        mkv_proc = subprocess.Popen(
            mkv_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert mkv_proc.stdout is not None

        try:
            # log to db
            request_id = create_new_request(
                cli_cmd="rip",
                cli_params=params_dict,
                exc_cmd=mkv_command_str,
                pid=mkv_proc.pid,
                parent_pid=os.getpid(),
            )

        except Exception as e:
            mkv_proc.send_signal(signal.SIGTERM)
            raise e

        interrupted = False
        try:
            yield from mkv_proc.stdout
        except KeyboardInterrupt as e:
            mkv_proc.send_signal(signal.SIGINT)
            interrupted = True
            raise InterruptedError("MakeMKV aborted!") from e
        finally:
            res = mkv_proc.wait()
            # TODO: makemkvcon does not output anything to stderr, so there will be no informative error messages. However, robust logging MSG details will likely fix this issue
            complete_request(request_id, res)
            if res != 0 and not interrupted:
                raise RuntimeError(f"makemkvcon failed with exit code {res}")
