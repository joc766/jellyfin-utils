import subprocess
from pathlib import Path


# TODO: verify/add support for non-disk drives to allow testing with backed-up data
class MakeMKVClient:
    def __init__(self, executable: str = "makemkvcon"):
        self.executable = executable

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

    def start_mkv_process(
        self, drive_name: str, output_path: Path, cache_size: int = 512, title_id: int | None = None
    ):
        if title_id is None:
            title = "all"
        else:
            title = str(title_id)

        mkv_proc = subprocess.Popen(
            [
                self.executable,
                "mkv",
                "-r",
                f"--cache={cache_size}",
                drive_name,
                title,
                output_path,
                "--progress=-stdout",
                "--messages=-same",
            ],
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
