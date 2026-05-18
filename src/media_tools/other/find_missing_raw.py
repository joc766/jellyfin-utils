import os
from pathlib import Path

import paramiko

JELLYFIN_HOST = os.getenv("JELLYFIN_SERVER", "192.168.50.2")
JELLYFIN_USER = os.getenv("JELLYFIN_USER", "jackoconnor")
JELLYFIN_BASE = Path(os.getenv("JELLYFIN_BASE", "/mnt/storage/jellyfin"))


def find_missing_raw_movies() -> list[str]:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.connect(JELLYFIN_HOST, username=JELLYFIN_USER)
        with client.open_sftp() as sftp_client:
            compressed_dirs = set(sftp_client.listdir(str(JELLYFIN_BASE / "compressed" / "movie")))
            raw_dirs = set(sftp_client.listdir(str(JELLYFIN_BASE / "raw" / "movie")))

    return [str(Path(dir).stem) for dir in compressed_dirs - raw_dirs]
