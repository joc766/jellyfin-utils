from pathlib import Path

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


# TODO: option to rip largest title, interactive mode, or all content on disc
# TODO: dipslay some printed output for each major step and/or display a separate step counter
def rip_disk(verbose: bool = False, output_base: Path | None = None):

    drive_name = None
    mkv_client = MakeMKVClient()

    drive_info_parser = MKVInfoParser()
    try:
        for line in mkv_client.get_info_lines():
            drive_info_parser.handle_line(line)
    finally:
        drive_info = drive_info_parser.extract_active_drive()
        if drive_info is not None:
            drive_name, _, _, _ = drive_info

    assert drive_name is not None
    disc_info_parser = MKVInfoParser()
    try:
        for line in mkv_client.get_info_lines(drive_name):
            disc_info_parser.handle_line(line)
    finally:
        disc_info = disc_info_parser.build()

    return disc_info

    # MakeMKV mkv rip step: track progress
    # output_path = output_base / disc_name
    #
    # cache_size = None
    # if disc_info.disc_type == "BD":
    #     cache_size = 1024
    # elif disc_info.disc_type == "DVD":
    #     cache_size = 512
    #
    # assert cache_size is not None
    #
    # check_existing_mkvs(output_path)
    #
    # mkv_proc = subprocess.Popen(
    #     [
    #         "makemkvcon",
    #         "mkv",
    #         "-r",
    #         f"--cache={cache_size}",
    #         "--progress=-stdout",
    #         raw_drive_name,
    #         "all",
    #         output_path,
    #     ],
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.STDOUT,
    #     text=True,
    #     bufsize=1,
    # )
    #
    # assert mkv_proc.stdout is not None
    #
    # MakeMKVProgressTracker(mkv_proc.stdout).track_progress()
    #
    # return mkv_proc.wait()
