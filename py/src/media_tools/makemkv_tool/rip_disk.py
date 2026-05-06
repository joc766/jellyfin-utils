from pathlib import Path

from media_tools.makemkv_tool.progress_tracker import MakeMKVProgressTracker

from .client import MakeMKVClient
from .info_parser import MKVInfoParser


def check_existing_mkvs(output_path):
    # Handle existing MKVs in output path
    if not output_path.exists():
        output_path.mkdir()

    existing_mkvs = list(output_path.glob("*.mkv"))
    if len(existing_mkvs) > 0:
        clear_dir = input(
            f"""{output_path} contains MKV files. Would you
                like to continue and overwrite these files? (y/N): """
        )
        if clear_dir == "Y" or clear_dir == "y":
            for file in existing_mkvs:
                file.unlink()

    return


# TODO: improve title selection so you can see all titles
# instead of one at a time
# TODO: make more testable with mock data for the mkv ripping step
def rip_disk(output_base: Path, verbose: bool = False, overwrite: bool = False):

    drive_name = None
    mkv_client = MakeMKVClient()

    # TODO: this can be done better by using `drutil` to save time (however, may be less compatible)
    drive_info_parser = MKVInfoParser()
    print("Identifying active drives...")
    try:
        for line in mkv_client.get_info_lines():
            drive_info_parser.handle_line(line)
    finally:
        drive_info = drive_info_parser.extract_active_drive()
        if drive_info is not None:
            drive_name, _, _, _ = drive_info

    assert drive_name is not None
    disc_info_parser = MKVInfoParser()
    print("Extracting disc information...")
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
        response = input(
            f"{title.title_name} (title_id {title.title_id}) has duration {title.duration}. Would you like to rip it? (y/N): "
        )
        if response in ("y", "Y", "Yes", "yes", "YES"):
            titles_to_rip.append(title.title_id)

    print("Beginning makemkvcon...")
    for i, title_id in enumerate(titles_to_rip):
        print(f"Ripping title_id {title_id} ({i}/{len(titles_to_rip)})")
        mkv_progress = MakeMKVProgressTracker()
        for line in mkv_client.start_mkv_process(
            drive_name, output_path, cache_size=cache_size, title_id=title_id
        ):
            if verbose:
                print(line)
            mkv_progress.handle_line(line)
