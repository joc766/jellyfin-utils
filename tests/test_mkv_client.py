import pytest
from rich.console import Console

from media_tools.makemkv_tool import MakeMKVClient


def test_info_intterupt(tmp_path):
    client = MakeMKVClient(output_base=tmp_path, console=Console())
    with pytest.raises(InterruptedError):
        generator = client.get_info_lines()
        next(generator)
        generator.throw(KeyboardInterrupt)


# def test_mkv_intterupt(tmp_path):
#     # TODO: mock client.disc_info
#     client = MakeMKVClient(output_base=tmp_path, console=Console())
#     with pytest.raises(InterruptedError):
#         generator = client.run_makemkv()
#         next(generator)
#         generator.throw(KeyboardInterrupt)
