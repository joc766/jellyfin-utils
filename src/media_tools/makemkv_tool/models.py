from dataclasses import dataclass, field
from typing import Literal

DiscType = Literal["BD", "DVD"]


@dataclass
class InfoEvent:
    raw_line: str


# Drive scan messages
# DRV:index,visible,enabled,flags,drive name,disc name
@dataclass
class DriveInfoEvent(InfoEvent):
    index: int
    drive_name: str
    disc_name: str
    os_path: str


# Disc, title and stream information
# CINFO:id,code,value
# TINFO:id,code,value
# SINFO:id,code,value
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


@dataclass
class MakeMKVStreamInfo:
    type: str = ""
    format: str = ""
    bitrate: str = ""
    dimensions: str | None = None
    aspect_ratio: str | None = None
    framerate: str | None = None
    audio_type: str | None = None
    audio_lang: str | None = None


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
    drive_name: str = ""
    disc_title: str = ""
    disc_type: DiscType | None = None
    titles: dict[int, MakeMKVTitleInfo] = field(default_factory=dict)


@dataclass
class ProgEvent:
    raw_line: str


@dataclass
class ProgTotalEvent(ProgEvent):
    code: str
    name: str


@dataclass
class ProgCurrEvent(ProgEvent):
    code: str
    name: str


@dataclass
class ProgValueEvent(ProgEvent):
    current: int
    total: int
    max: int


@dataclass
class MakeMKVProgressState:
    prog_total: int | None
    prog_curr: int | None
    total_size: int
    curr_size: int
    status: str
    total_task_name: str = ""
    curr_task_name: str = ""
