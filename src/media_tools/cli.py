import os
from dataclasses import dataclass
from pathlib import Path

import click
from dotenv import load_dotenv
from InquirerPy.base.control import Choice
from InquirerPy.prompts.list import ListPrompt
from rich.console import Console

from media_tools.rsync_tool.models import ContentFormat, ContentType

from .ffmpeg_tool import compress_mkv
from .makemkv_tool import rip_disk
from .omdb_tool import OmdbClient
from .rsync_tool import RsyncClient, interactive_sync

# TODO: add a setup command to create a config with
# info like the base dir for everyting and the target server
# TODO: command to eject disk tray (with default /dev/disk6)


@dataclass(frozen=True)
class AppConfig:
    jellyfin_base: Path
    jellyfin_host: str
    jellyfin_user: str
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
    load_dotenv(dotenv_path)

    return AppConfig(
        local_base=Path(require_env("LOCAL_BASE")),
        jellyfin_base=Path(require_env("JELLYFIN_BASE")),
        jellyfin_user=require_env("JELLYFIN_USER"),
        jellyfin_host=require_env("JELLYFIN_HOST"),
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
    if not env_path.is_file():
        raise click.ClickException(f"No .env file found in {str(env_path.parent)}")
    config = load_config(env_path)
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
@click.option("--verbose", "-v", is_flag=True)
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
    verbose: bool = False,
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
@click.pass_obj
def upload_to_server(
    app_ctx: AppContext, content_type: ContentType, content_format: ContentFormat, verbose: bool
):
    client = RsyncClient.from_config(
        app_ctx.config,
        console=app_ctx.console,
        direction="upload",
        content_format=content_format,
        content_type=content_type,
    )
    interactive_sync(client, verbose=verbose)


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


def main():
    cli()


if __name__ == "__main__":
    main()
