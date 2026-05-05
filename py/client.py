import re
import subprocess


class MakeMKVClient:
    def __init__(self, executable: str = "makemkvcon"):
        self.executable = executable
        self.raw_drive_name = None
        self.disc_name = None
        self.os_disc_path = None

    def identify_disc_drive(self):
        # TODO: use MakeMKVProgressTracker and Popen

        # MakeMKV info step: extract correct drive number
        info_pattern = re.compile("^DRV:(.*)$", re.IGNORECASE)
        info_result = subprocess.run(
            ["makemkvcon", "info", "-r", "--cache=1", "info", "disc:9999"],
            capture_output=True,
            text=True,
        )

        disc_name = None
        raw_drive_name = None
        os_disc_path = None
        for line in info_result.stdout.splitlines():
            match = info_pattern.search(line)
            if match:
                drive_info = match.group(1)
                raw_drive_name, _, _, _, _, disc_name, os_disc_path = drive_info.split(
                    ","
                )
                disc_name = disc_name.replace('"', "")
                os_disc_path = os_disc_path.replace('"', "")
                if len(disc_name) > 0:
                    raw_drive_name = "disc:" + raw_drive_name

                    break

        assert disc_name is not None
        assert raw_drive_name is not None
        assert os_disc_path is not None

        self.disc_name = disc_name
        self.raw_drive_name = raw_drive_name
        self.os_disc_path = os_disc_path

    def get_info_lines(self):
        assert self.raw_drive_name is not None
        info_proc = subprocess.Popen(
            [
                "makemkvcon",
                "-r",
                "--cache=16",
                "info",
                "--progress=-stdout",
                self.raw_drive_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert info_proc.stdout is not None

        # TODO: this doesn't work! the progress tracker is taking stdout away
        # adjust the approach to send each line to both the progress parser
        # and the Info Parser in real-time.
        try:
            for line in info_proc.stdout:
                yield line
        finally:
            result = info_proc.wait()
            if result != 0:
                raise RuntimeError(f"makemkvcon failed with exit code {result}")
