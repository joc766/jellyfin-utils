import os
from pathlib import Path

import click
from dotenv import load_dotenv

from .ffmpeg_tool import compress_mkv
from .makemkv_tool import rip_disk

STORAGE_BASE = Path(os.getenv("STORAGE_BASE", "/Volumes/SanDisk"))
RAW_STORAGE_BASE = STORAGE_BASE / "raw"
COMPRESSED_STORAGE_BASE = STORAGE_BASE / "compressed"

load_dotenv(override=False)


@click.group()
def cli():
    pass


@cli.command("rip")
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--verbose", "-v", is_flag=True)
def rip_disk_cmd(content_type, verbose):
    output_base = RAW_STORAGE_BASE / content_type.lower()
    rip_disk(verbose, output_base)


@cli.command("compress")
@click.option("--dvd", "-d", "disc_type", flag_value="DVD", default=True)
@click.option("--bd", "-b", "disc_type", flag_value="BD")
@click.option("--overwrite", "-f", "overwrite", is_flag=True)
@click.option("--output", "-o", "output_path", type=click.Path(path_type=Path))
@click.argument("input_path", type=click.Path(path_type=Path))
def compress_mkv_cmd(
    input_path: Path, disc_type: str, overwrite: bool, output_path: Path | None = None
):
    compress_mkv(input_path, disc_type, overwrite=overwrite, output_path=output_path)


# @click.command()
# @click.option("--dvd", "-d", "disc_type", flag_value="DVD")
# @click.option("--bd", "-b", "disc_type", flag_value="BD", default=True)
# @click.option("--tv", "content_type", flag_value="tv")
# @click.option("--movie", "content_type", flag_value="movie", default=True)
# @click.option("--output", "-o", "output_dir", type=click.Path(path_type=Path))
# @click.argument("input_path", type=click.Path(path_type=Path))
# def compress_mkv(input_path: Path, output_dir: Path, disc_type: str, content_type: str):
#     ff = FFmpeg()
#     if not input_path.is_file():
#         if not input_path.stem.endswith("_original"):
#             raise ValueError(f"input_path must end with _original")
#         raise ValueError(f"input_path ({input_path}) is not a file.")
#     if not output_dir.is_dir():
#         raise ValueError(f"output_dir ({output_dir}) is not a directory.")
#
#     output_path = output_dir / f"{input_path.stem.replace('_original', '')}.mp4"
#
#     ff_command = (
#         ff.input(input_path, map=["v:0", "a:0"])
#         .codec("libx264 -preset slow -crf 18 -px_fmt yuv420p", "v")
#         .options(
#             [
#                 "profile:v high -level 4.1",
#                 "maxrate 20M -bufsize 20M",
#                 "x264-params interlaced=0",
#                 "-movflags +faststart",
#                 "-fflags +genpts -avoid_negative_ts make_zero",
#             ]
#         )
#         .codec("libfdk_aac -ac 2 -ab 256k", "a")
#         .disable("s")
#         .output(output_path)
#     )
#
#     if disc_type == "DVD":
#         ff_command = ff_command.filter(
#             "trunc(480*dar/2)*2:480:flags=lanczos,setsar=1,setfield=prog", "v"
#         )
#
#     print(ff_command.get_args())


def main():
    cli()


if __name__ == "__main__":
    main()
