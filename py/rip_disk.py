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
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class InfoEvent:
    raw_line: str


@dataclass
class DiscInfoEvent(InfoEvent):
    key: str
    value: str


@dataclass
class TitleInfoEvent(InfoEvent):
    title_id: int
    key: str
    value: str


@dataclass
class StreamInfoEvent(InfoEvent):
    title_id: int
    stream_id: int
    key: str
    value: str


DISC_FIELD_MAP = {1: "disc_type", 2: "disc_title"}


TITLE_FIELD_MAP = {
    8: "chapter_count",
    9: "duration",
    10: "size_human",
    11: "size_bytes",
    27: "title_name",
}


STREAM_INFO_MAP = {
    1: "type",
    2: "audio_type",
    3: "audio_lang",
    5: "format",
    13: "bitrate",
    19: "dimensions",
    20: "aspect_ratio",
    21: "framerate",
}


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


class MakeMKVClient:
    def __init__(self, executable: str = "makemkvcon"):
        self.executable = executable
        self.raw_drive_name = None
        self.disc_name = None
        self.os_disc_path = None

    def identify_disc_drive(self):
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

    def get_info_lines(self) -> list:
        assert self.raw_drive_name is not None
        result = subprocess.run(
            ["makemkvcon", "-r", "--cache=16", "info", self.raw_drive_name],
            capture_output=True,
            text=True,
        )

        assert result.stdout is not None

        return result.stdout.splitlines()


class MakeMKVInfoBuilder:
    def __init__(self):
        self.disc_info: MakeMKVDiscInfo = MakeMKVDiscInfo()

    def apply(self, event: InfoEvent):
        match event:
            case DiscInfoEvent():
                self.apply_disc_info(event)
            case TitleInfoEvent():
                self.apply_title_info(event)
            case StreamInfoEvent():
                self.apply_stream_info(event)

    def apply_disc_info(self, event: DiscInfoEvent):
        match event.key:
            case "disc_type":
                if event.value == "DVD disc":
                    disc_type = "DVD"
                else:
                    disc_type = "BD"
                self.disc_info.disc_type = disc_type
            case "disc_title":
                self.disc_info.disc_title = event.value

    def get_title(self, title_id: int) -> MakeMKVTitleInfo:
        if title_id not in self.disc_info.titles.keys():
            self.disc_info.titles[title_id] = MakeMKVTitleInfo(title_id=title_id)
        return self.disc_info.titles[title_id]

    def apply_title_info(self, event: TitleInfoEvent):
        title = self.get_title(event.title_id)
        match event.key:
            case "chapter_count":
                title.chapter_count = int(event.value)
            case "duration":
                title.duration = event.value
            case "size_human":
                title.size_human = event.value
            case "size_bytes":
                title.size_bytes = int(event.value)
            case "title_name":
                title.title_name = event.value

    def get_stream(self, title_id: int, stream_id: int) -> MakeMKVStreamInfo:
        title = self.get_title(title_id)
        if stream_id not in title.streams.keys():
            title.streams[stream_id] = MakeMKVStreamInfo()
        return title.streams[stream_id]

    def apply_stream_info(self, event: StreamInfoEvent):
        stream = self.get_stream(event.title_id, event.stream_id)
        match event.key:
            case "type":
                stream.type = event.value
            case "audio_type":
                stream.audio_type = event.value
            case "audio_lang":
                stream.audio_lang = event.value
            case "format":
                stream.format = event.value
            case "bitrate":
                stream.bitrate = event.value
            case "dimensions":
                stream.dimensions = event.value
            case "aspect_ratio":
                stream.aspect_ratio = event.value
            case "framerate":
                stream.framerate = event.value

    def build(self) -> MakeMKVDiscInfo:
        return self.disc_info


class MKVInfoParser:
    def __init__(self):
        self.disc_info_pattern = re.compile('^CINFO:(\\d+),(\\d+),"([^"]+)"$')
        self.title_info_pattern = re.compile('^TINFO:(\\d+),(\\d+),(\\d+),"([^"]+)"$')
        self.stream_info_pattern = re.compile(
            '^SINFO:(\\d+),(\\d+),(\\d+),(\\d+),"([^"]+)"$'
        )

        self.builder = MakeMKVInfoBuilder()

    def parse(self, lines: list) -> MakeMKVDiscInfo:
        for line in lines:
            if line[0:6] in ("CINFO:", "TINFO:", "SINFO:"):
                event = self.parse_line(line)
                if event is not None:
                    self.builder.apply(event)

        return self.builder.build()

    def parse_line(self, line: str) -> InfoEvent | None:
        if disc_info_match := self.disc_info_pattern.match(line):
            event_code = int(disc_info_match.group(1))
            # ignore lines that we do not care about
            if event_code in DISC_FIELD_MAP.keys():
                disc_info_event = DiscInfoEvent(
                    key=DISC_FIELD_MAP[event_code],
                    value=disc_info_match.group(3),
                    raw_line=line,
                )
                return disc_info_event

        elif title_info_match := self.title_info_pattern.match(line):
            event_code = int(title_info_match.group(2))
            # ignore lines that we do not care about
            if event_code in TITLE_FIELD_MAP.keys():
                title_info_event = TitleInfoEvent(
                    title_id=int(title_info_match.group(1)),
                    key=TITLE_FIELD_MAP[event_code],
                    value=title_info_match.group(4),
                    raw_line=line,
                )
                return title_info_event

        elif stream_info_match := self.stream_info_pattern.match(line):
            event_code = int(stream_info_match.group(3))
            # ignore lines that we do not care about
            if event_code in STREAM_INFO_MAP.keys():
                stream_info_event = StreamInfoEvent(
                    title_id=int(stream_info_match.group(1)),
                    stream_id=int(stream_info_match.group(2)),
                    key=STREAM_INFO_MAP[event_code],
                    value=stream_info_match.group(5),
                    raw_line=line,
                )
                return stream_info_event


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

    mkv_client = MakeMKVClient()

    mkv_client.identify_disc_drive()
    lines = mkv_client.get_info_lines()

    disc_info = MKVInfoParser().parse(lines)

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
