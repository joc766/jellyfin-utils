import subprocess


class MakeMKVClient:
    def __init__(self, executable: str = "makemkvcon"):
        self.executable = executable

    def get_info_lines(self, drive_name: str = "disc:9999", cache_size=16):
        info_proc = subprocess.Popen(
            [
                "makemkvcon",
                "-r",
                f"--cache={cache_size}",
                "info",
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
            for line in info_proc.stdout:
                yield line
        finally:
            res = info_proc.wait()
            if res != 0:
                raise RuntimeError(f"makemkvcon failed with exit code {res}")
