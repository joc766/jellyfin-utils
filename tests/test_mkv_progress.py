from pathlib import Path
from time import sleep

from rich.console import Console

from media_tools.makemkv_tool.progress import MakeMKVProgressTracker
from media_tools.makemkv_tool.render import MakeMKVProgressRenderer

DATA_DIR = Path(__file__).resolve().parent / "data"


def test_mkv_progress_info(testing_mode: bool = False):
    console = Console()
    test_file = (DATA_DIR / "full-info-prog-output.txt").open(
        mode="r", buffering=1, encoding="utf-8"
    )
    mkv_progress = MakeMKVProgressTracker()
    with MakeMKVProgressRenderer(console=console) as progress_render:
        mkv_progress.update_status("Running [repr.filename]makemkvcon info[/repr.filename]")
        for prog_state in mkv_progress.track_progress(test_file):
            progress_render.update(prog_state)
            if testing_mode:
                sleep(0.25)


def test_mkv_progress_mkv(testing_mode: bool = False):
    console = Console()
    test_file = (DATA_DIR / "full-mkv-prog-output.txt").open(
        mode="r", buffering=1, encoding="utf-8"
    )
    mkv_progress = MakeMKVProgressTracker()
    with MakeMKVProgressRenderer(console=console) as progress_render:
        for prog_state in mkv_progress.track_progress(test_file):
            progress_render.update(prog_state)
            if testing_mode:
                sleep(0.01)


def test_rip_disk_progress(testing_mode: bool = False):
    mkv_progress = MakeMKVProgressTracker()
    with MakeMKVProgressRenderer(console=Console()) as progress_render:
        test_drive_info_file = (DATA_DIR / "drive-info-test.txt").open(
            mode="r", buffering=1, encoding="utf-8"
        )
        mkv_progress.update_status(
            "Running [repr.filename]makemkvcon info[/repr.filename] (drive info)"
        )
        for curr_state in mkv_progress.track_progress(test_drive_info_file):
            progress_render.update(curr_state)
            if testing_mode:
                sleep(0.05)

        test_disc_info_file = (DATA_DIR / "full-info-prog-output.txt").open(
            mode="r", buffering=1, encoding="utf-8"
        )
        mkv_progress.update_status(
            "Running [repr.filename]makemkvcon info[/repr.filename] (disc info)"
        )
        for curr_state in mkv_progress.track_progress(test_disc_info_file):
            progress_render.update(curr_state)
            if testing_mode:
                if curr_state.prog_total is not None:
                    sleep(0.01)
                else:
                    sleep(0.0001)

        test_mkv_file = (DATA_DIR / "full-mkv-prog-output.txt").open(
            mode="r", buffering=1, encoding="utf-8"
        )
        mkv_progress.update_status("Running [repr.filename]makemkvcon mkv[/repr.filename]")
        for curr_state in mkv_progress.track_progress(test_mkv_file):
            progress_render.update(curr_state)
            if testing_mode:
                if curr_state.total_task_name == "Saving all titles to MKV files":
                    sleep(0.0001)
                else:
                    sleep(0.01)
