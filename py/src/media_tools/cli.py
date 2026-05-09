from pathlib import Path

import click
from dotenv import load_dotenv
from rich import get_console

from .ffmpeg_tool import compress_mkv
from .makemkv_tool import rip_disk
from .omdb_tool import MissingCredentialsError, rename_movie

load_dotenv("/Users/linkit/Projects/gh/jellyfin-utils/.env", override=False)
console = get_console()


@click.group()
def cli():
    pass


@cli.command("organize")
@click.argument("path", type=click.Path(path_type=Path))
@click.argument("imdb_id", type=str)
def organize_cmd(path: Path, imdb_id: str):
    try:
        rename_movie(path, imdb_id)
    except MissingCredentialsError as e:
        raise click.ClickException(str(e)) from e


@cli.command("rip")
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--output_base", "-o", "output_base", type=click.Path(path_type=Path))
@click.option("--overwrite", is_flag=True, default=False)
def rip_disk_cmd(
    output_base: Path, content_type: str, verbose: bool = False, overwrite: bool = False
):
    rip_disk(content_type, output_base=output_base, verbose=verbose, overwrite=overwrite)


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
    try:
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
    except Exception as e:
        raise click.ClickException(str(e)) from e


def main():
    cli()


if __name__ == "__main__":
    main()
