"""Tools to automate the ffmpeg compression processes"""

from .client import FFmpegClient
from .compress_mkv import compress_mkv

__all__ = ["FFmpegClient", "compress_mkv"]
