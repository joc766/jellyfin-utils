from dataclasses import dataclass, field
from typing import Optional


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
