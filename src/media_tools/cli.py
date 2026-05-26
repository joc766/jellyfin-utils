import os
from dataclasses import dataclass
from pathlib import Path

import click
from dotenv import load_dotenv
from InquirerPy.base.control import Choice
from InquirerPy.prompts.list import ListPrompt
from rich.console import Console
from rich.table import Table

from .ffmpeg_tool import FFmpegClient, compress_mkv
from .makemkv_tool import MakeMKVClient, rip_disk
from .omdb_tool import OmdbClient
from .rsync_tool import ContentFormat, ContentType, RsyncClient, interactive_sync
from .sftp_tool import JellyfinSFTPClient, get_imdb_id

# TODO: add a setup command to create a config with
# TODO: command to eject disk tray (with default /dev/disk6)
# TODO: add command to safely delete from local_base when jellyfin_base has src


@dataclass(frozen=True)
class AppConfig:
    jellyfin_base: Path
    jellyfin_host: str | None
    jellyfin_user: str | None
    local_base: Path
    omdb_api_key: str


@dataclass(frozen=True)
class AppContext:
    config: AppConfig
    console: Console


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config(dotenv_path: Path | None = None) -> AppConfig:
    if dotenv_path is not None and not dotenv_path.is_file():
        raise FileNotFoundError(f"No .env file found in {str(dotenv_path.parent)}")

    load_dotenv(dotenv_path)

    return AppConfig(
        local_base=Path(require_env("LOCAL_BASE")),
        jellyfin_base=Path(require_env("JELLYFIN_BASE")),
        jellyfin_user=os.getenv("JELLYFIN_USER"),
        jellyfin_host=os.getenv("JELLYFIN_HOST"),
        omdb_api_key=require_env("OMDB_API_KEY"),
    )


@click.group()
@click.pass_context
@click.option("--env-file", "env_file", type=click.Path(path_type=Path))
def cli(ctx: click.Context, env_file: Path | None = None):
    if not env_file:
        home_dir = Path(require_env("HOME"))
        env_path = home_dir / ".config" / "media-tools" / ".env"
    else:
        env_path = env_file
    try:
        config = load_config(env_path)
    except (RuntimeError, FileNotFoundError) as e:
        raise click.ClickException(str(e)) from e
    ctx.obj = AppContext(config=config, console=Console())


@cli.command("organize")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--show", "content_type", flag_value="show")
@click.argument("imdb_id", type=str)
@click.pass_obj
def organize_cmd(app_ctx: AppContext, imdb_id: str, content_type: str):
    client = OmdbClient(app_ctx.config.omdb_api_key)
    title = client.get_title(imdb_id)
    console = app_ctx.console
    content_base = app_ctx.config.local_base / "raw" / content_type
    folder_choices = [
        Choice(value=folder, name=folder.stem)
        for folder in content_base.iterdir()
        if folder.is_dir()
    ]
    path = ListPrompt(
        f"Select the folder for {title}",
        choices=folder_choices,
        vi_mode=True,
    ).execute()
    console.print(f"mv '{path}' '{path.parent / title}'")
    try:
        client.rename_movie(path, imdb_id)
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
        rip_disk(client, verbose=verbose, debug=debug)
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command("compress")
@click.option("--dvd", "-d", "disc_type", flag_value="DVD", default=True)
@click.option("--bd", "-b", "disc_type", flag_value="BD")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--overwrite", "-f", "overwrite", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_obj
def compress_mkv_cmd(
    app_ctx: AppContext,
    disc_type: str,
    content_type: str,
    overwrite: bool,
    verbose: bool = False,
):
    compressed_storage_base = app_ctx.config.local_base / "compressed" / content_type
    raw_storage_base = app_ctx.config.local_base / "raw" / content_type
    selected_folder = ListPrompt(
        message="Select a raw movie folder:",
        choices=[
            Choice(value=folder, name=folder.stem)
            for folder in raw_storage_base.iterdir()
            if folder.is_dir()
        ],
        vi_mode=True,
    ).execute()
    selected_movie = ListPrompt(
        message="Select a title to compress:",
        choices=[
            Choice(value=file, name=file.name)
            for file in selected_folder.iterdir()
            if file.is_file()
        ],
        vi_mode=True,
    ).execute()
    output_path: Path = (
        compressed_storage_base / selected_folder.stem / f"{selected_movie.stem}.mp4"
    )
    output_path.parent.mkdir(exist_ok=True)
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
        )
    except AssertionError as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command("upload")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--show", "content_type", flag_value="show", type=str)
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
    interactive_sync(client, verbose=verbose, debug=debug)


@cli.command("download")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--show", "content_type", flag_value="show", type=str)
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
    interactive_sync(client, verbose=verbose, debug=debug)


@cli.command("find-missing-raw")
@click.pass_obj
def find_missing_raw(app_ctx: AppContext):
    sftp_client = JellyfinSFTPClient.from_config(app_ctx.config)
    console = app_ctx.console
    missing_table = Table(title="Compressed movies with no raw backup on server")
    missing_table.add_column("movie_name")
    for movie_name in sorted(sftp_client.find_missing_raw_movies()):
        missing_table.add_row(movie_name)
    console.print(missing_table)


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


def main():
    cli()


if __name__ == "__main__":
    main()
