import re
from pathlib import Path

import paramiko


def get_imdb_id(folder_name: str) -> str | None:
    imdb_pattern = re.compile(r".*\[imdbid-(tt\d+)\]")
    if match := imdb_pattern.match(folder_name):
        return match.group(1)


class JellyfinSFTPClient:
    def __init__(self, jellyfin_host: str, jellyfin_user: str, jellyfin_base: Path):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(jellyfin_host, username=jellyfin_user)
        self.sftp_client = self.ssh_client.open_sftp()
        self.jellyfin_base = jellyfin_base

    @classmethod
    def from_config(cls, config):
        return JellyfinSFTPClient(config.jellyfin_host, config.jellyfin_user, config.jellyfin_base)

    def get_subdir_imdb_ids(self, *, content_type: str, content_format: str):
        return {
            get_imdb_id(str(folder)): folder
            for folder in self.sftp_client.listdir(
                str(self.jellyfin_base / content_format / content_type)
            )
            if get_imdb_id(str(folder)) is not None
        }

    def find_missing_raw_movies(self):
        compressed_dirs = self.get_subdir_imdb_ids(
            content_format="compressed", content_type="movie"
        )
        raw_dirs = self.get_subdir_imdb_ids(content_format="raw", content_type="movie")
        missing_ids = set(compressed_dirs.keys()) - set(raw_dirs.keys())

        return [
            str(Path(dir).name)
            for imdb_id, dir in compressed_dirs.items()
            if imdb_id in missing_ids
        ]

    def find_missing_compressed_movies(self):
        compressed_dirs = self.get_subdir_imdb_ids(
            content_format="compressed", content_type="movie"
        )
        raw_dirs = self.get_subdir_imdb_ids(content_format="raw", content_type="movie")
        missing_ids = set(raw_dirs.keys()) - set(compressed_dirs.keys())

        return [str(Path(dir).name) for imdb_id, dir in raw_dirs.items() if imdb_id in missing_ids]
