import re
from pathlib import Path

import paramiko


def get_imdb_id(folder_name: str) -> str | None:
    imdb_pattern = re.compile(r".*\[imdbid-(tt\d+)\]")
    if match := imdb_pattern.match(folder_name):
        return match.group(1)


def find_missing_raw_movies(
    jellyfin_host: str, jellyfin_user: str, jellyfin_base: Path
) -> list[str]:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.connect(jellyfin_host, username=jellyfin_user)
        with client.open_sftp() as sftp_client:
            compressed_dirs = {
                get_imdb_id(str(folder)): folder
                for folder in sftp_client.listdir(str(jellyfin_base / "compressed" / "movie"))
                if get_imdb_id(str(folder)) is not None
            }
            raw_dirs = {
                get_imdb_id(str(folder)): folder
                for folder in sftp_client.listdir(str(jellyfin_base / "raw" / "movie"))
                if get_imdb_id(str(folder)) is not None
            }
    missing_ids = set(compressed_dirs.keys()) - set(raw_dirs.keys())

    return [
        str(Path(dir).name) for imdb_id, dir in compressed_dirs.items() if imdb_id in missing_ids
    ]


def find_missing_compressed_movies(
    jellyfin_host: str, jellyfin_user: str, jellyfin_base: Path
) -> list[str]:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.connect(jellyfin_host, username=jellyfin_user)
        with client.open_sftp() as sftp_client:
            compressed_dirs = {
                get_imdb_id(str(folder)): folder
                for folder in sftp_client.listdir(str(jellyfin_base / "compressed" / "movie"))
                if get_imdb_id(str(folder)) is not None
            }
            raw_dirs = {
                get_imdb_id(str(folder)): folder
                for folder in sftp_client.listdir(str(jellyfin_base / "raw" / "movie"))
                if get_imdb_id(str(folder)) is not None
            }

    missing_ids = set(raw_dirs.keys()) - set(compressed_dirs.keys())

    return [str(Path(dir).name) for imdb_id, dir in raw_dirs.items() if imdb_id in missing_ids]
