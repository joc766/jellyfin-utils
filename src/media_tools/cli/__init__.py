"""
A CLI to orchestrate the `makemkvcon`, `ffmpeg`, `rsync`, and organizational
utilities used to maintain jellyfin server.
"""

from .config import load_config

__all__ = ["load_config"]
