from pathlib import Path

import paramiko


def find_missing_raw_movies(
    jellyfin_host: str, jellyfin_user: str, jellyfin_base: Path
) -> list[str]:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.connect(jellyfin_host, username=jellyfin_user)
        with client.open_sftp() as sftp_client:
            compressed_dirs = set(sftp_client.listdir(str(jellyfin_base / "compressed" / "movie")))
            raw_dirs = set(sftp_client.listdir(str(jellyfin_base / "raw" / "movie")))

    return [str(Path(dir).stem) for dir in compressed_dirs - raw_dirs]


def find_missing_compressed_movies(
    jellyfin_host: str, jellyfin_user: str, jellyfin_base: Path
) -> list[str]:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.connect(jellyfin_host, username=jellyfin_user)
        with client.open_sftp() as sftp_client:
            compressed_dirs = set(sftp_client.listdir(str(jellyfin_base / "compressed" / "movie")))
            raw_dirs = set(sftp_client.listdir(str(jellyfin_base / "raw" / "movie")))
            print(raw_dirs)
            print(compressed_dirs)

    return [str(Path(dir).stem) for dir in raw_dirs - compressed_dirs]
