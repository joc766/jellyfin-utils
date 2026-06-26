import shutil
from pathlib import Path
from typing import get_args

import click
from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.rawlist import RawlistPrompt
from rich.console import Console
from rich.table import Table

from media_tools.ffmpeg_tool.client import FFmpegClient
from media_tools.ffmpeg_tool.compress_mkv import compress_mkv

from .config import AppContext, load_config
from .makemkv_tool import MakeMKVClient, rip_disk
from .omdb_tool import (
    MovieTitleOptions,
    OmdbClient,
    TvTitleOptions,
    format_size_human,
    organize_movie_title,
    organize_tv_title,
)
from .rsync_tool import ContentFormat, ContentType, RsyncClient, interactive_sync
from .sftp_tool import JellyfinSFTPClient, get_imdb_id

# TODO: add a setup command to create a config with
# TODO: command to eject disk tray (with default /dev/disk6)


@click.group()
@click.pass_context
@click.option("--env-file", "env_file", type=click.Path(path_type=Path))
def cli(ctx: click.Context, env_file: Path | None = None):
    try:
        config = load_config(env_file)
    except (RuntimeError, FileNotFoundError) as e:
        raise click.ClickException(str(e)) from e
    ctx.obj = AppContext(config=config, console=Console())


@cli.command("organize")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.argument("imdb_id", type=str)
@click.pass_obj
def organize_cmd(app_ctx: AppContext, imdb_id: str, content_type: str):
    try:
        client = OmdbClient(app_ctx.config.omdb_api_key)
        omdb_title, omdb_year = client.get_title(imdb_id)
        content_base = app_ctx.config.local_base / "raw" / content_type
        folder_choices = [
            Choice(value=folder, name=folder.stem)
            for folder in content_base.iterdir()
            if folder.is_dir()
        ]
        title_folder: Path = ListPrompt(
            f"Select the folder for {omdb_title}",
            choices=folder_choices,
            vi_mode=True,
        ).execute()

        title_options = (
            list(get_args(TvTitleOptions))
            if content_type == "tv"
            else list(get_args(MovieTitleOptions))
        )
        for title_file in title_folder.iterdir():
            file_size = format_size_human(title_file.stat().st_size)
            title_type = RawlistPrompt(
                message=f"Select content type for {title_file.name} ({file_size})",
                choices=title_options,
                vi_mode=True,
                transformer=lambda result: f"{result}",
            ).execute()
            match content_type:
                case "tv":
                    if title_type != "ignore":
                        season = (
                            InputPrompt(message="Enter Season Number: ").execute().rjust(2, "0")
                        )
                        episode = (
                            InputPrompt(message="Enter Episode Number: ").execute().rjust(2, "0")
                        )
                        organize_tv_title(
                            content_base,
                            title_file,
                            title_type,
                            omdb_title,
                            omdb_year,
                            imdb_id,
                            season,
                            episode,
                        )
                case "movie":
                    organize_movie_title(
                        content_base, title_file, title_type, omdb_title, omdb_year, imdb_id
                    )
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command("rip")
@click.option("--verbose", "-v", is_flag=True)
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--debug", "debug", is_flag=True)
@click.pass_obj
def rip_disk_cmd(
    app_ctx: AppContext, content_type: ContentType, verbose: bool = False, debug: bool = False
):
    try:
        output_base = app_ctx.config.local_base / "raw" / content_type
        client = MakeMKVClient(output_base=output_base, console=app_ctx.console)
        rip_disk(client, verbose=verbose, debug=debug, console=app_ctx.console)
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command("compress")
@click.option("--dvd", "-d", "disc_type", flag_value="DVD", default=True)
@click.option("--bd", "-b", "disc_type", flag_value="BD")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--overwrite", "-f", "overwrite", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--single-audio", "single_audio", is_flag=True)
@click.option("--preserve-surround", "preserve_surround", is_flag=True)
@click.option("--crf", "crf", type=int, default=18)
@click.option("--preset", "preset", type=str, default="slow")
@click.option("--dry-run", "dry_run", is_flag=True)
@click.pass_obj
def compress_mkv_cmd(
    app_ctx: AppContext,
    disc_type: str,
    content_type: str,
    overwrite: bool,
    verbose: bool = False,
    preserve_surround: bool = False,
    single_audio: bool = False,
    crf: int | None = None,
    preset: str = "slow",
    dry_run: bool = False,
):
    compressed_storage_base = app_ctx.config.local_base / "compressed" / content_type
    raw_storage_base = app_ctx.config.local_base / "raw" / content_type
    selected_folder: Path = ListPrompt(
        message="Select a raw movie folder:",
        choices=[
            Choice(value=folder, name=folder.stem)
            for folder in raw_storage_base.iterdir()
            if folder.is_dir()
        ],
        vi_mode=True,
    ).execute()
    selected_files = CheckboxPrompt(
        message="Select a title to compress:",
        choices=[
            Choice(value=file, name=str(file.relative_to(selected_folder)))
            for file in sorted(selected_folder.rglob("*"), key=lambda k: k.name)
            if file.is_file() and file.suffix in (".mkv", "mp4", ".mov")
        ],
        vi_mode=True,
    ).execute()

    for selected_movie in selected_files:
        output_path: Path = compressed_storage_base / selected_movie.relative_to(
            raw_storage_base
        ).with_suffix(".mp4")
        output_path.parent.mkdir(exist_ok=True, parents=True)
        client = FFmpegClient(
            input_path=selected_movie,
            output_path=output_path,
            console=app_ctx.console,
            source_type=disc_type,
        )
        try:
            compress_mkv(
                client,
                overwrite=overwrite,
                verbose=verbose,
                single_audio=single_audio,
                preserve_surround_track=preserve_surround,
                crf=crf,
                preset=preset,
                dry_run=dry_run,
            )
        except AssertionError as e:
            raise e
        except Exception as e:
            raise click.ClickException(str(e)) from e


@cli.command("upload")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--compressed", "content_format", flag_value="compressed", default=True, type=str)
@click.option("--raw", "content_format", flag_value="raw", type=str)
@click.option("--verbose", "-v", "verbose", is_flag=True)
@click.option("--debug", "debug", is_flag=True)
@click.pass_obj
def upload_to_server(
    app_ctx: AppContext,
    content_type: ContentType,
    content_format: ContentFormat,
    verbose: bool,
    debug: bool,
):
    client = RsyncClient.from_config(
        app_ctx.config,
        console=app_ctx.console,
        direction="upload",
        content_format=content_format,
        content_type=content_type,
    )
    try:
        interactive_sync(client, verbose=verbose, debug=debug)
    except AssertionError as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command("download")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--compressed", "content_format", flag_value="compressed", default=True, type=str)
@click.option("--raw", "content_format", flag_value="raw", type=str)
@click.option("--verbose", "-v", "verbose", is_flag=True)
@click.option("--debug", "debug", is_flag=True)
@click.pass_obj
def download_from_server(
    app_ctx: AppContext,
    content_type: ContentType,
    content_format: ContentFormat,
    verbose: bool = False,
    debug: bool = False,
):
    client = RsyncClient.from_config(
        app_ctx.config,
        console=app_ctx.console,
        direction="download",
        content_format=content_format,
        content_type=content_type,
    )
    try:
        interactive_sync(client, verbose=verbose, debug=debug)
    except AssertionError as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command("find-missing-raw")
@click.pass_obj
def find_missing_raw(app_ctx: AppContext):
    sftp_client = JellyfinSFTPClient.from_config(app_ctx.config)
    console = app_ctx.console
    missing_table = Table(title="Compressed movies with no raw backup on server")
    missing_table.add_column("movie_name")
    for movie_name in sorted(sftp_client.find_missing_raw_movies()):
        missing_table.add_row(movie_name)
    console.print(missing_table, markup=False)


@cli.command("find-missing-compressed")
@click.pass_obj
def find_missing_compressed(app_ctx: AppContext):
    sftp_client = JellyfinSFTPClient.from_config(app_ctx.config)
    console = app_ctx.console
    missing_table = Table(title="Raw movies with no compressed version on server")
    missing_table.add_column("movie_name")
    for movie_name in sorted(sftp_client.find_missing_compressed_movies()):
        missing_table.add_row(movie_name)
    console.print(missing_table)


@cli.command("safe-remove")
@click.option("--raw", "content_format", flag_value="raw", type=str, default=True)
@click.option("--compressed", "content_format", flag_value="compressed", type=str)
@click.option("--movie", "content_type", flag_value="movie", type=str, default=True)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--show", "content_type", flag_value="show", type=str)
@click.pass_obj
def safe_removal(app_ctx: AppContext, content_format: ContentFormat, content_type: ContentType):
    """Get files that can be safely removed by comparing RsyncClient.get_new_files() to all folders"""
    rsync_client = RsyncClient.from_config(
        config=app_ctx.config,
        console=app_ctx.console,
        direction="upload",
        content_type=content_type,
        content_format=content_format,
    )
    local_path = app_ctx.config.local_base / content_format / content_type
    all_folder_info = {
        get_imdb_id(str(folder.stem)): folder for folder in local_path.iterdir() if folder.is_dir()
    }
    all_folder_ids = {imdb_id for imdb_id in all_folder_info.keys()}
    missing_folder_info = rsync_client.get_new_files()
    missing_folder_ids = {get_imdb_id(folder_name) for folder_name in missing_folder_info.keys()}
    deletable_ids = all_folder_ids - missing_folder_ids
    deletable_folders = [v for k, v in all_folder_info.items() if k in deletable_ids]
    if len(deletable_folders) > 0:
        selected = CheckboxPrompt(
            message=f"Select which titles you would like to remove from {app_ctx.config.local_base}",
            choices=[
                Choice(value=folder_path, name=folder_path.stem)
                for folder_path in deletable_folders
            ],
            vi_mode=True,
        ).execute()

        for folder_path in selected:
            shutil.rmtree(folder_path)
            app_ctx.console.print(f"Deleted '{folder_path}'", markup=False)
    else:
        app_ctx.console.print("No deletable folders were found.")


def main():
    cli()


if __name__ == "__main__":
    main()
