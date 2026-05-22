import subprocess
from pathlib import Path

from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from rich.console import Console
from rich.prompt import Confirm

from media_tools.makemkv_tool.info_parser import MKVInfoParser

from .models import MakeMKVTitleInfo


# TODO: verify/add support for non-disk drives to allow testing with backed-up data
class MakeMKVClient:
    def __init__(self, *, output_base: Path, console: Console, executable: str = "makemkvcon"):
        self.executable: str = executable
        self.console = console
        self.drive_name = self.extract_drive_name()
        self.disc_info = self.extract_disc_info()
        self.output_path = output_base / self.disc_info.disc_title
        self.check_existing_mkvs()

    def extract_drive_name(self):
        self.console.print("Identifying active drives...")
        drive_info_parser = MKVInfoParser()
        try:
            for line in self.get_info_lines():
                drive_info_parser.handle_line(line)
        finally:
            drive_info = drive_info_parser.extract_active_drive()
            if drive_info is not None:
                drive_name, _, _, _ = drive_info
            else:
                raise ValueError("Drive name not found")

        return drive_name

    def extract_disc_info(self):
        disc_info_parser = MKVInfoParser()
        self.console.print("Extracting disc information...")
        try:
            for line in self.get_info_lines(self.drive_name):
                disc_info_parser.handle_line(line)
        finally:
            disc_info = disc_info_parser.build()

        return disc_info

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

        try:
            yield from info_proc.stdout
        finally:
            res = info_proc.wait()
            if res != 0:
                raise RuntimeError(f"makemkvcon failed with exit code {res}")

    @property
    def cache_size(self) -> int | None:
        return 512 if self.disc_info.disc_type == "DVD" else 1024

    def start_mkv_process(self, title_id: int | None = None, debug: bool = False):
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
            self.output_path,
            "--progress=-stdout",
            "--messages=-same",
        ]
        if debug:
            self.console.print(mkv_command)
        mkv_proc = subprocess.Popen(
            mkv_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert mkv_proc.stdout is not None

        try:
            yield from mkv_proc.stdout
        finally:
            res = mkv_proc.wait()
            if res != 0:
                raise RuntimeError(f"makemkvcon failed with exit code {res}")

    def check_existing_mkvs(self):
        # Handle existing MKVs in output path
        if not self.output_path.exists():
            self.output_path.mkdir()

        existing_mkvs = list(self.output_path.glob("*.mkv"))
        if len(existing_mkvs) > 0:
            if Confirm.ask(
                f"{self.output_path} contains MKV files. Would you like to continue and overwrite these files?"
            ):
                for file in existing_mkvs:
                    file.unlink()
            else:
                raise FileExistsError(f"{self.output_path} contains MKV files.")
        return

    def prompt_for_titles(self) -> list[MakeMKVTitleInfo]:
        selected_titles = CheckboxPrompt(
            message="Select titles to rip:",
            choices=[
                Choice(title.title_id, name=f"{title.title_name} (duration: {title.duration})")
                for title in self.disc_info.titles.values()
            ],
            vi_mode=True,
            transformer=lambda result: (
                f"{len(result)} title{'s' if len(result) > 1 else ''} selected"
            ),
        ).execute()
        titles_to_rip: list[MakeMKVTitleInfo] = [
            self.disc_info.titles[title_id] for title_id in selected_titles
        ]
        return titles_to_rip
