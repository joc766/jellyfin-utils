import re
import shlex
import subprocess
import sys
from pathlib import Path

CROP_PATTERN = re.compile(r"^.*(crop=\d+:\d+:\d+:\d+)$")


def crop_detect(path: Path, debug=False) -> str:
    command = (
        "ffmpeg",
        "-ss",
        "900",
        "-i",
        str(path),
        "-t",
        "10",
        "-vf",
        "scale=round(iw*sar/2)*2:ih:flags=lanczos,cropdetect",
        "-an",
        "-f",
        "null",
        "-",
    )
    if debug:
        print(shlex.join(command))
    result = subprocess.run(command, capture_output=True, text=True, check=True, encoding="utf-8")
    stderr: str = result.stderr

    match = None
    for line in stderr.splitlines():
        if match := CROP_PATTERN.match(line):
            break

    if match is None:
        raise Exception("Pattern not found")

    return match.group(1)


if __name__ == "__main__":
    print(crop_detect(Path(sys.argv[1])))
