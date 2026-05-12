import os
from pathlib import Path
from rich import get_console

from rich.prompt import Confirm

from .client import MakeMKVClient
from .info_parser import MKVInfoParser
from .progress import MakeMKVProgressTracker

STORAGE_BASE = Path(os.getenv("STORAGE_BASE", "/Volumes/SanDisk"))
RAW_STORAGE_BASE = STORAGE_BASE / "raw"

console = get_console()


# TODO maybe move this into the client?
def check_existing_mkvs(output_path):
    # Handle existing MKVs in output path
    if not output_path.exists():
        output_path.mkdir()

    existing_mkvs = list(output_path.glob("*.mkv"))
    if len(existing_mkvs) > 0:
        if Confirm.ask(
            f"{output_path} contains MKV files. Would you like to continue and overwrite these files?"
        ):
            for file in existing_mkvs:
                file.unlink()

    return


# TODO: improve title selection so you can see all titles instead of one at a time
# TODO: add dry run option for easier testing
# TODO: Handle cleaning file names to proper directory names
def rip_disk(
    content_type: str = "DVD",
    output_base: Path | None = None,
    verbose: bool = False,
    overwrite: bool = False,
):
    if output_base is None:
        output_base = RAW_STORAGE_BASE / content_type

    drive_name = None
    mkv_client = MakeMKVClient()

    # TODO: this can be done better by using `drutil` to save time (however, may be less compatible)
    drive_info_parser = MKVInfoParser()
    console.print("Identifying active drives...")
    try:
        for line in mkv_client.get_info_lines():
            drive_info_parser.handle_line(line)
    finally:
        drive_info = drive_info_parser.extract_active_drive()
        if drive_info is not None:
            drive_name, _, _, _ = drive_info

    assert drive_name is not None
    disc_info_parser = MKVInfoParser()
    console.print("Extracting disc information...")
    try:
        for line in mkv_client.get_info_lines(drive_name):
            disc_info_parser.handle_line(line)
    finally:
        disc_info = disc_info_parser.build()

    disc_title = disc_info.disc_title

    # MakeMKV mkv rip step: track progress
    output_path = output_base / disc_title

    cache_size = None
    if disc_info.disc_type == "BD":
        cache_size = 1024
    elif disc_info.disc_type == "DVD":
        cache_size = 512

    assert cache_size is not None

    if not overwrite:
        check_existing_mkvs(output_path)

    titles = disc_info.titles.values()
    titles_to_rip = []
    for title in titles:
        if Confirm.ask(
            f"{title.title_name} (title_id {title.title_id}) has duration {title.duration}. Would you like to rip it?"
        ):
            titles_to_rip.append((title.title_id, title.title_name))

    console.print("Beginning makemkvcon...")
    for i, title_info in enumerate(titles_to_rip):
        title_id, title_name = title_info
        console.print(f"Ripping {title_name} ({i + 1}/{len(titles_to_rip)})")
        mkv_progress = MakeMKVProgressTracker()
        try:
            for line in mkv_client.start_mkv_process(
                drive_name, output_path, cache_size=cache_size, title_id=title_id
            ):
                if verbose:
                    console.print(line)
                mkv_progress.handle_line(line)
        finally:
            if not mkv_progress.finished:
                mkv_progress.stop_progress()
