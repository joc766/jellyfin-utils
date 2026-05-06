from os import path
from pathlib import Path

import click
from dotenv import load_dotenv

from .ffmpeg_tool import compress_mkv
from .makemkv_tool import rip_disk


load_dotenv(override=False)


@click.group()
def cli():
    pass


@cli.command("rip")
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--output_base", "-o", "output_base", type=click.Path(path_type=Path))
def rip_disk_cmd(output_base: Path, content_type: str, verbose: bool = False):
    rip_disk(content_type, output_base=output_base, verbose=verbose)


@cli.command("compress")
@click.option("--dvd", "-d", "disc_type", flag_value="DVD", default=True)
@click.option("--bd", "-b", "disc_type", flag_value="BD")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--overwrite", "-f", "overwrite", is_flag=True)
@click.option("--output", "-o", type=click.Path(path_type=Path))
@click.option("--output_dir", "output_dir", type=click.Path(path_type=Path))
@click.option("--output_filename", "output_filename", type=str)
@click.option("--container", "-c", "container", type=str, default="mp4")
@click.argument("input_path", type=click.Path(path_type=Path))
def compress_mkv_cmd(
    input_path: Path,
    disc_type: str,
    content_type: str,
    overwrite: bool,
    container: str,
    output: Path | None = None,
    output_dir: Path | None = None,
    output_filename: str | None = None,
):
    compress_mkv(
        input_path,
        disc_type,
        content_type=content_type,
        output=output,
        output_dir=output_dir,
        output_filename=output_filename,
        output_container=container,
        overwrite=overwrite,
    )


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
