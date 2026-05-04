import re
import subprocess

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class MakeMKVStreamInfo:
    type: str = ""
    format: str = ""
    bitrate: str = ""
    dimensions: Optional[str] = None
    aspect_ratio: Optional[str] = None
    framerate: Optional[str] = None
    audio_type: Optional[str] = None
    audio_lang: Optional[str] = None


@dataclass
class MakeMKVTitleInfo:
    title_id: int = -1
    chapter_count: int = 0
    duration: str = ""
    size_human: str = ""
    size_bytes: int = 0
    title_name: str = ""
    streams: dict[int, MakeMKVStreamInfo] = field(default_factory=dict)


@dataclass
class MakeMKVDiscInfo:
    disc_title: str = ""
    disc_type: str = ""
    titles: dict[int, MakeMKVTitleInfo] = field(default_factory=dict)


def identify_mkv_lines(line: str):
    pass


def identify_disc_drive() -> Tuple[str, str, str]:
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


# TODO: refactor function to reduce cyclomatic complexity
def extract_disc_info(raw_drive_name: str) -> MakeMKVDiscInfo:
    """
    Extract disc info using `makemkvcon -r --cache=16 info [raw_drive_name].

    Parses information into a MakeMKVInfo object.
    """

    result = subprocess.run(
        ["makemkvcon", "-r", "--cache=16", "info", raw_drive_name],
        capture_output=True,
        text=True,
    )

    assert result.stdout is not None

    disc_title_pattern = re.compile('^CINFO:(\\d+),(\\d+),"([^"]+)"$')
    title_info_pattern = re.compile('^TINFO:(\\d+),(\\d+),(\\d+),"([^"]+)"$')
    stream_info_pattern = re.compile('^SINFO:(\\d+),(\\d+),(\\d+),(\\d+),"([^"]+)"$')

    disc_info: MakeMKVDiscInfo = MakeMKVDiscInfo()
    curr_title: MakeMKVTitleInfo = MakeMKVTitleInfo(title_id=0)
    curr_title_num: int = 0
    curr_stream: MakeMKVStreamInfo = MakeMKVStreamInfo()
    curr_stream_num: int = 0

    for line in result.stdout.splitlines():
        if disc_title_match := disc_title_pattern.match(line):
            info_code = int(disc_title_match.group(1))
            info_value = disc_title_match.group(3)
            if info_code == 2:
                disc_info.disc_title = str(info_value)
            elif info_code == 1:
                if info_value == "DVD disc":
                    disc_info.disc_type = "DVD"
                elif info_value == "Blu-ray disc":
                    disc_info.disc_type = "BD"

        elif title_info_match := title_info_pattern.match(line):
            title_num = int(title_info_match.group(1))
            info_code = int(title_info_match.group(2))
            info_value = title_info_match.group(4)

            if title_num != curr_title_num:
                # Add current title info to disc_info.titles and reset stream
                curr_title.streams[curr_stream_num] = curr_stream
                disc_info.titles[curr_title_num] = curr_title
                curr_title = MakeMKVTitleInfo(title_id=title_num)
                curr_title_num = title_num
                curr_stream_num = 0
                curr_stream = MakeMKVStreamInfo()

            if info_code == 8:
                curr_title.chapter_count = int(info_value)
            elif info_code == 9:
                curr_title.duration = str(info_value)
            elif info_code == 10:
                curr_title.size_human = str(info_value)
            elif info_code == 11:
                curr_title.size_bytes = int(info_value)
            elif info_code == 27:
                curr_title.title_name = str(info_value)

        elif stream_info_match := stream_info_pattern.match(line):
            title_num = int(stream_info_match.group(1))
            stream_num = int(stream_info_match.group(2))
            stream_info_code = int(stream_info_match.group(3))
            stream_info_value = stream_info_match.group(5)

            if stream_num != curr_stream_num:
                # Add current stream to title_info.streams
                curr_title.streams[curr_stream_num] = curr_stream
                curr_stream_num = stream_num
                curr_stream = MakeMKVStreamInfo()

            if stream_info_code == 1:
                curr_stream.type = str(stream_info_value)
            elif stream_info_code == 5:
                curr_stream.format = str(stream_info_value)
            elif stream_info_code == 13:
                curr_stream.bitrate = str(stream_info_value)
            elif stream_info_code == 19:
                curr_stream.dimensions = str(stream_info_value)
            elif stream_info_code == 20:
                curr_stream.aspect_ratio = str(stream_info_value)
            elif stream_info_code == 21:
                curr_stream.framerate = str(stream_info_value)
            elif stream_info_code == 2:
                curr_stream.audio_type = str(stream_info_value)
            elif stream_info_code == 3:
                curr_stream.audio_lang = str(stream_info_value)

    curr_title.streams[curr_stream_num] = curr_stream
    disc_info.titles[curr_title_num] = curr_title

    assert disc_info is not None
    return disc_info


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


# TODO: option to rip largest title, interactive mode, or all content on disc
def rip_disk(verbose: bool, output_base: Path):

    raw_drive_name, disc_name, _ = identify_disc_drive()
    disc_info = extract_disc_info(raw_drive_name)

    # MakeMKV mkv rip step: track progress
    output_path = output_base / disc_name

    cache_size = None
    if disc_info.disc_type == "BD":
        cache_size = 1024
    elif disc_info.disc_type == "DVD":
        cache_size = 512

    assert cache_size is not None

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
