from pathlib import Path
from time import sleep

from rich.console import Console

from media_tools.rsync_tool import RsyncClient, RsyncProgressTracker, RsyncRender

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

    with open(DATA_DIR / "rsync-sample-log.txt", "rb") as f:
        progress = RsyncProgressTracker(title_name="rsync-sample-log")
        with RsyncRender(
            title_name="rsync-sample-log", direction="upload", console=client.console
        ) as render:
            for curr_state in progress.track(client._get_chunks(f)):
                render.update(curr_state)
                if slow:
                    if curr_state.remaining_transfers == 0:
                        sleep(1)
                    else:
                        sleep(0.005)
