import subprocess
import re

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from pathlib import Path
from typing import Tuple


def identify_mkv_lines(line: str):
    pass


def extract_disc_info() -> Tuple[str, str, str]:
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
            raw_drive_name, _, _, _, _, disc_name, os_disc_path = drive_info.split(",")
            disc_name = disc_name.replace('"', "")
            os_disc_path = os_disc_path.replace('"', "")
            if len(disc_name) > 0:
                raw_drive_name = "disc:" + raw_drive_name

                break

    assert disc_name is not None
    assert raw_drive_name is not None
    assert os_disc_path is not None

    return raw_drive_name, disc_name, os_disc_path


def check_existing_mkvs(output_path):
    # Handle existing MKVs in output path
    if not output_path.exists():
        output_path.mkdir()

    existing_mkvs = list(output_path.glob("*.mkv"))
    if len(existing_mkvs) > 0:
        clear_dir = input(
            f"""{output_path} contains MKV files. Would you
                like to continue and overwrite these files? (y/N): """
        )
        if clear_dir == "Y" or clear_dir == "y":
            for file in existing_mkvs:
                file.unlink()

    return


def rip_disk(verbose: bool, output_base: Path):

    raw_drive_name, disc_name, _ = extract_disc_info()

    # MakeMKV mkv rip step: track progress
    output_path = output_base / disc_name
    cache_size = 1024  # TODO get full disc info, adjust based on DVD vs BD

    check_existing_mkvs(output_path)

    mkv_proc = subprocess.Popen(
        [
            "makemkvcon",
            "mkv",
            "-r",
            f"--cache={cache_size}",
            "--progress=-stdout",
            raw_drive_name,
            "all",
            output_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert mkv_proc.stdout is not None

    total_prog_pattern = re.compile('^PRGT:(\\d+),(\\d+),"([^"]+)"')
    curr_prog_pattern = re.compile('^PRGC:(\\d+),(\\d+),"([^"]+)"')
    mkv_pattern = re.compile("^PRGV:(\\d+),(\\d+),(\\d+)$")
    total_task = None
    curr_task = None
    with Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>5.1f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        for line in mkv_proc.stdout:
            line = line.rstrip("\n")
            if verbose:
                print(line)

            if total_prog_match := total_prog_pattern.match(line):
                message = total_prog_match.group(3)
                if total_task is not None:
                    progress.update(total_task, completed=65536)
                total_task = progress.add_task(f"[green]{message}", total=65536)

            elif curr_prog_match := curr_prog_pattern.match(line):
                message = curr_prog_match.group(3)
                if curr_task is not None:
                    progress.update(curr_task, completed=65536, visible=False)
                curr_task = progress.add_task(f"[blue]{message}", total=65536)

            elif mkv_match := mkv_pattern.match(line):
                curr_prog = int(mkv_match.group(1))
                total_prog = int(mkv_match.group(2))
                # max_value = int(mkv_match.group(3))

                if curr_task is not None:
                    progress.update(curr_task, completed=curr_prog)
                if total_task is not None:
                    progress.update(total_task, completed=total_prog)

    return mkv_proc.wait()
