import re

from .models import (
    DiscInfoEvent,
    DriveInfoEvent,
    InfoEvent,
    MakeMKVDiscInfo,
    MakeMKVStreamInfo,
    MakeMKVTitleInfo,
    StreamInfoEvent,
    TitleInfoEvent,
)


class MakeMKVInfoBuilder:
    def __init__(self):
        self.drives: list[DriveInfoEvent] = []
        self.disc_info: MakeMKVDiscInfo = MakeMKVDiscInfo()

    def apply(self, event: InfoEvent):
        match event:
            case DriveInfoEvent():
                self.add_drive(event)
            case DiscInfoEvent():
                self.apply_disc_info(event)
            case TitleInfoEvent():
                self.apply_title_info(event)
            case StreamInfoEvent():
                self.apply_stream_info(event)

    def add_drive(self, event: DriveInfoEvent):
        self.drives.append(event)

    def apply_disc_info(self, event: DiscInfoEvent):
        match event.key:
            case "disc_type":
                if event.value == "DVD disc":
                    disc_type = "DVD"
                else:
                    disc_type = "BD"
                self.disc_info.disc_type = disc_type
            case "disc_title":
                self.disc_info.disc_title = re.sub(r"[-./]", "", event.value)

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

    def extract_active_drive(self):
        for drive in self.drives:
            if len(drive.disc_name) > 0:
                return (
                    f"disc:{drive.index}",
                    drive.drive_name,
                    drive.disc_name,
                    drive.os_path,
                )

    def build(self) -> MakeMKVDiscInfo:
        return self.disc_info


class MakeMKVInfoParser:
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

    def __init__(self):
        self.drive_info_pattern = re.compile(
            '^DRV:(\\d+),\\d+,\\d+,\\d+,"([^"]+)","([^"]+)","([^"]+)"$'
        )
        self.disc_info_pattern = re.compile('^CINFO:(\\d+),(\\d+),"([^"]+)"$')
        self.title_info_pattern = re.compile('^TINFO:(\\d+),(\\d+),(\\d+),"([^"]+)"$')
        self.stream_info_pattern = re.compile('^SINFO:(\\d+),(\\d+),(\\d+),(\\d+),"([^"]+)"$')
        self.builder = MakeMKVInfoBuilder()

    def parse(self, lines: list) -> MakeMKVDiscInfo:
        for line in lines:
            self.handle_line(line)

        return self.build()

    def handle_line(self, line: str):
        if line[0:4] in ("CINF", "TINF", "SINF", "DRV:"):
            event = self.parse_line(line)
            if event is not None:
                self.builder.apply(event)

    def parse_line(self, line: str) -> InfoEvent | None:

        if drive_info_match := self.drive_info_pattern.match(line):
            drive_info_event = DriveInfoEvent(
                index=int(drive_info_match.group(1)),
                drive_name=drive_info_match.group(2),
                disc_name=drive_info_match.group(3),
                os_path=drive_info_match.group(4),
                raw_line=line,
            )
            return drive_info_event

        if disc_info_match := self.disc_info_pattern.match(line):
            event_code = int(disc_info_match.group(1))
            # ignore lines that we do not care about
            if event_code in self.DISC_FIELD_MAP.keys():
                disc_info_event = DiscInfoEvent(
                    key=self.DISC_FIELD_MAP[event_code],
                    value=disc_info_match.group(3),
                    raw_line=line,
                )
                return disc_info_event

        elif title_info_match := self.title_info_pattern.match(line):
            event_code = int(title_info_match.group(2))
            # ignore lines that we do not care about
            if event_code in self.TITLE_FIELD_MAP.keys():
                title_info_event = TitleInfoEvent(
                    title_id=int(title_info_match.group(1)),
                    key=self.TITLE_FIELD_MAP[event_code],
                    value=title_info_match.group(4),
                    raw_line=line,
                )
                return title_info_event

        elif stream_info_match := self.stream_info_pattern.match(line):
            event_code = int(stream_info_match.group(3))
            # ignore lines that we do not care about
            if event_code in self.STREAM_INFO_MAP.keys():
                stream_info_event = StreamInfoEvent(
                    title_id=int(stream_info_match.group(1)),
                    stream_id=int(stream_info_match.group(2)),
                    key=self.STREAM_INFO_MAP[event_code],
                    value=stream_info_match.group(5),
                    raw_line=line,
                )
                return stream_info_event

    def extract_active_drive(self):
        return self.builder.extract_active_drive()

    def build(self):
        return self.builder.build()
