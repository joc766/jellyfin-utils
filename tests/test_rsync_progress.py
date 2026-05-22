from pathlib import Path
from time import sleep

from rich.console import Console

from media_tools.rsync_tool import RsyncClient, RsyncProgressTracker

DATA_DIR = Path(__file__).resolve().parent / "data"


def test_rsync_progress(slow: bool = False):
    client = RsyncClient(
        jellyfin_base=Path(""),
        jellyfin_host="",
        jellyfin_user="",
        local_base=Path(""),
        console=Console(),
        direction="upload",
        content_format="compressed",
        content_type="movie",
    )
    progress = RsyncProgressTracker()

    with open(DATA_DIR / "rsync-sample-log.txt", "rb") as f:
        try:
            for line in client._get_chunks(f):
                progress.handle_line(line)
                if slow:
                    if progress.finalizing:
                        sleep(1)
                    else:
                        sleep(0.005)
        finally:
            if not progress.stopped:
                progress.stop_progress()
