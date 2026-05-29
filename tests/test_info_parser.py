from pathlib import Path

from media_tools.makemkv_tool.info_parser import MakeMKVInfoParser
from media_tools.makemkv_tool.models import MakeMKVDiscInfo

DATA_DIR = Path(__file__).resolve().parent / "data"


def test_drive_info_parse():
    lines = (DATA_DIR / "drive-info-test.txt").read_text(encoding="utf-8").splitlines()
    parser = MakeMKVInfoParser()
    for line in lines:
        parser.handle_line(line)

    drive_info = parser.extract_active_drive()

    assert drive_info is not None
    mkv_drive_name, full_drive_name, disc_name, os_path = drive_info

    assert mkv_drive_name == "disc:0"
    assert full_drive_name == "BD-ROM hp DVDWBD SN-406AB HH01 R90Q6YLD900132"
    assert disc_name == "THE_BRUTALIST"
    assert os_path == "/dev/rdisk6"


def test_info_parser_total():
    lines = (DATA_DIR / "full-disc-info.txt").read_text(encoding="utf-8").splitlines()

    disc_info: MakeMKVDiscInfo = MakeMKVInfoParser().parse(lines)
    assert disc_info.disc_title == "INCEPTION"
    assert disc_info.disc_type == "DVD"
    assert len(disc_info.titles.keys()) == 2
    assert len(disc_info.titles[0].streams.keys()) == 6
    assert len(disc_info.titles[1].streams.keys()) == 4
    assert disc_info.titles[0].title_name == "A1_t00.mkv"
    assert disc_info.titles[0].streams[0].type == "Video"
