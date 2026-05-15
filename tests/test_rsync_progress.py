from pathlib import Path
from time import sleep

from media_tools.rsync_tool import RsyncClient, RsyncProgressTracker

client = RsyncClient()

DATA_DIR = Path(__file__).resolve().parent / "data"


def test_rsync_progress(slow: bool = False):
    client = RsyncClient()
    progress = RsyncProgressTracker()

    with open(DATA_DIR / "rsync-sample-log.txt", "rb") as f:
        try:
            for line in client.get_chunks(f):
                progress.handle_line(line)
                if slow:
                    if progress.finalizing:
                        sleep(1)
                    else:
                        sleep(0.005)
        finally:
            if not progress.stopped:
                progress.stop_progress()
