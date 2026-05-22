"""
A CLI to orchestrate the `makemkvcon`, `ffmpeg`, `rsync`, and organizational
utilities used to maintain jellyfin server.
"""

from .cli import load_config

__all__ = ["load_config"]
