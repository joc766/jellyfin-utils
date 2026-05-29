from pathlib import Path
from time import sleep

from rich.console import Console

from media_tools.makemkv_tool.progress import MakeMKVProgressTracker

DATA_DIR = Path(__file__).resolve().parent / "data"


def test_mkv_progress_info(testing_mode: bool = False):
    test_file = (DATA_DIR / "full-info-prog-output.txt").open(
        mode="r", buffering=1, encoding="utf-8"
    )
    with MakeMKVProgressTracker(test_file, console=Console()) as progress:
        progress.track_progress(testing_mode=testing_mode)


def test_mkv_progress_mkv(testing_mode: bool = False):
    test_file = (DATA_DIR / "full-mkv-prog-output.txt").open(
        mode="r", buffering=1, encoding="utf-8"
    )
    with MakeMKVProgressTracker(test_file, console=Console()) as progress:
        progress.track_progress(testing_mode=testing_mode)


def test_rip_disk_progress(testing_mode: bool = False):
    console = Console()
    with MakeMKVProgressTracker(console=console) as mkv_progress:
        test_drive_info_file = (DATA_DIR / "drive-info-test.txt").open(
            mode="r", buffering=1, encoding="utf-8"
        )
        mkv_progress.set_status("Extracting drive info...")
        for line in test_drive_info_file:
            mkv_progress.handle_line(line)
            if testing_mode:
                sleep(0.1)

        test_disc_info_file = (DATA_DIR / "full-info-prog-output.txt").open(
            mode="r", buffering=1, encoding="utf-8"
        )
        mkv_progress.set_status("Extracting disc info...")
        for line in test_disc_info_file:
            mkv_progress.handle_line(line)
            if testing_mode:
                sleep(0.025)

        test_mkv_file = (DATA_DIR / "full-mkv-prog-output.txt").open(
            mode="r", buffering=1, encoding="utf-8"
        )
        mkv_progress.set_status("Running makemkvcon...")
        for line in test_mkv_file:
            mkv_progress.handle_line(line)
            if testing_mode:
                sleep(0.001)
