from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# TODO: this is just a type hint, it doesn't actually enforce anything. need something better than a literal
Libx264Tune = Literal["film", "animation", "grain", None]

Libx264Preset = Literal[
    "veryslow", "slower", "slow", "medium", "fast", "faster", "veryfast", "superfast", "ultrafast"
]


class FFProbeDispositionInfo(BaseModel):
    default: bool = False
    original: bool = False


class FFProbeTagInfo(BaseModel):
    language: str
    title: str | None = None
    duration_eng: timedelta = Field(alias="DURATION-eng")
    number_of_bytes_eng: str = Field(alias="NUMBER_OF_BYTES-eng")
    bps_eng: str = Field(alias="BPS-eng")

    @field_validator("duration_eng", mode="before")
    @classmethod
    def parse_duration_eng(cls, value: str) -> timedelta:
        hours, minutes, seconds = value.split(":")

        return timedelta(
            hours=int(hours),
            minutes=int(minutes),
            seconds=float(seconds),
        )


class BaseFFprobeStreamInfo(BaseModel):
    index: int
    codec_name: str
    codec_type: str
    start_pts: int
    start_time: str
    disposition: FFProbeDispositionInfo
    tags: FFProbeTagInfo


class FFProbeAudioStreamInfo(BaseFFprobeStreamInfo):
    sample_rate: str
    bit_rate: str | None = None
    channels: int
    channel_layout: str


class FFProbeVideoStreamInfo(BaseFFprobeStreamInfo):
    profile: str
    width: int
    height: int
    pix_fmt: str
    level: int
    field_order: str
    sample_aspect_ratio: str
    display_aspect_ratio: str
