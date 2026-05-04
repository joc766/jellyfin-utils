from rip_disk import MKVInfoParser, MakeMKVDiscInfo


def test_info_parser_total():
    with open("data/full-disc-info.txt", "r") as f:
        lines = f.read().splitlines()

    disc_info: MakeMKVDiscInfo = MKVInfoParser().parse(lines)
    assert disc_info.disc_title == "INCEPTION"
    assert disc_info.disc_type == "DVD"
    assert len(disc_info.titles.keys()) == 2
    assert len(disc_info.titles[0].streams.keys()) == 6
    assert len(disc_info.titles[1].streams.keys()) == 4
    assert disc_info.titles[0].title_name == "A1_t00.mkv"
    assert disc_info.titles[0].streams[0].type == "Video"
