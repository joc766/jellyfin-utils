from os import sync
from pathlib import Path

import click
from dotenv import load_dotenv
from rich import get_console

from .ffmpeg_tool import compress_mkv
from .makemkv_tool import rip_disk
from .omdb_tool import MissingCredentialsError, rename_movie
from .rsync_tool import interactive_sync

# TODO: re-examine the behavior of load_dotenv, may want to replace it with a proper configuration system
load_dotenv("/Users/linkit/Projects/gh/jellyfin-utils/.env", override=False)

console = get_console()

# TODO: add a setup command to create a config with
# info like the base dir for everyting and the target server
# TODO: Add organize_files functionality
# TODO: implement OMDB API calls
# TODO: delete files after successful sync to server?
# TODO: command that shows files in your compressed/raw base dirs that are not on the server
# TODO: command to eject disk tray (with default /dev/disk6)


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
    except Exception as e:
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


@cli.command("push")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--compressed", "content_format", flag_value="compressed", default=True)
@click.option("--raw", "content_format", flag_value="raw")
def sync_to_server(content_type: str, content_format: str):
    # TODO: add part where we prompt the user for options to upload based on content_type and content_format
    interactive_sync(content_type, content_format)


def main():
    cli()


if __name__ == "__main__":
    main()
