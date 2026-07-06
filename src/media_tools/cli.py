import shutil
from pathlib import Path
from typing import get_args

import click
from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.rawlist import RawlistPrompt
from prompt_toolkit.validation import ValidationError, Validator
from rich.console import Console
from rich.table import Table
from rich.text import Text

from media_tools.config import AppContext, load_config
from media_tools.db.connection import complete_request, create_new_request
from media_tools.ffmpeg_tool.client import FFmpegClient
from media_tools.ffmpeg_tool.compress_mkv import compress_mkv
from media_tools.makemkv_tool import MakeMKVClient, rip_disk
from media_tools.omdb_tool import (
    MovieTitleOptions,
    OmdbClient,
    TvTitleOptions,
    format_size_human,
    organize_movie_title,
    organize_tv_title,
)
from media_tools.rsync_tool.client import RsyncClient
from media_tools.rsync_tool.models import ContentFormat, ContentType
from media_tools.rsync_tool.progress import RsyncProgressTracker
from media_tools.rsync_tool.render import RsyncRender
from media_tools.sftp_tool import JellyfinSFTPClient, get_imdb_id

# TODO: add commands to suppress progress tracking
# TODO: log files
# TODO: move functions to separate module and just add them as commands


class AllowedValuesValidator(Validator):
    def __init__(self, allowed_values: set):
        self._message: str = f"Input should be in {allowed_values}"
        self._allowed_values = allowed_values

    def validate(self, document) -> None:
        try:
            val = int(document.text)
            if val not in self._allowed_values:
                raise ValueError("Invalid integer value.")
        except ValueError as e:
            raise ValidationError(
                message=self._message, cursor_position=document.cursor_position
            ) from e


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
        raise e


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
        raw_storage_base = app_ctx.config.local_base / "raw" / content_type
        rip_disk(
            raw_storage_base=raw_storage_base, verbose=verbose, debug=debug, console=app_ctx.console
        )
    except InterruptedError as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise e


@cli.command("sample-audios")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.pass_obj
def sample_audios(app_ctx: AppContext, content_type: ContentType):
    raw_storage_base = app_ctx.config.local_base / "raw" / content_type
    selected_folder: Path = ListPrompt(
        message="Select a raw folder:",
        choices=[
            Choice(value=folder, name=folder.stem)
            for folder in raw_storage_base.iterdir()
            if folder.is_dir()
        ],
        vi_mode=True,
    ).execute()
    selected_file = ListPrompt(
        message="Select a title:",
        choices=[
            Choice(value=file, name=str(file.relative_to(selected_folder)))
            for file in sorted(selected_folder.rglob("*"), key=lambda k: k.name)
            if file.is_file() and file.suffix in (".mkv", "mp4", ".mov")
        ],
        vi_mode=True,
    ).execute()
    client = FFmpegClient(input_path=selected_file)
    table = Table(title=f"Audio streams for {selected_file.stem}", show_lines=True)
    table.add_column("stream_index")
    table.add_column("codec_name")
    table.add_column("channels")
    audios = client.probe_audios()
    for audio_info in audios:
        table.add_row(str(audio_info.index), audio_info.codec_name, str(audio_info.channels))
    app_ctx.console.print(table)
    play = ConfirmPrompt(
        message="Would you like to play one of the above audios?", default=False
    ).execute()

    while play:
        selected_index = InputPrompt(
            message="Enter the stream index to sample:",
            validate=AllowedValuesValidator({x.index for x in audios}),
        ).execute()
        client.play_audio(selected_index)
        play = ConfirmPrompt(message="Play another sample?", default=False).execute()


@cli.command("compress")
@click.option("--dvd", "-d", "disc_type", flag_value="DVD", default=True)
@click.option("--bd", "-b", "disc_type", flag_value="BD")
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--overwrite", "-f", "overwrite", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--single-audio", "single_audio", is_flag=True)
@click.option("--preserve-surround", "preserve_surround", is_flag=True)
@click.option("--height", "height", type=int, default=None)
@click.option("--crf", "crf", type=int, default=None)
@click.option("--preset", "preset", type=str, default="slow")
@click.option("--dry-run", "dry_run", is_flag=True)
@click.option("--silent", "silent", is_flag=True)
@click.pass_obj
def compress_mkv_cmd(
    app_ctx: AppContext,
    disc_type: str,
    content_type: str,
    overwrite: bool,
    verbose: bool = False,
    preserve_surround: bool = False,
    single_audio: bool = False,
    height: int | None = None,
    crf: int | None = None,
    preset: str = "slow",
    dry_run: bool = False,
    silent: bool = False,
):
    params_dict = {
        k: v
        for k, v in locals().items()
        if k
        in (
            "disc_type",
            "content_type",
            "overwrite",
            "verbose",
            "single_audio",
            "preserve_surround",
            "height",
            "crf",
            "preset",
            "dry_run",
            "silent",
        )
    }

    compressed_storage_base = app_ctx.config.local_base / "compressed" / content_type
    raw_storage_base = app_ctx.config.local_base / "raw" / content_type
    try:
        selected_folder: Path = ListPrompt(
            message=f"Select a raw {content_type} folder:",
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
    except KeyboardInterrupt:
        raise

    for selected_movie in selected_files:
        request_id = create_new_request(cli_cmd="compress", cli_params=params_dict)
        try:
            compress_mkv(
                input_path=selected_movie,
                input_base=raw_storage_base,
                output_base=compressed_storage_base,
                source_type=disc_type,
                request_id=request_id,
                overwrite=overwrite,
                verbose=verbose,
                single_audio=single_audio,
                preserve_surround_track=preserve_surround,
                height=height,
                crf=crf,
                preset=preset,
                console=app_ctx.console,
                dry_run=dry_run,
                silent=silent,
            )
        except AssertionError as e:
            raise e
        except (RuntimeError, FileExistsError, InterruptedError) as e:
            raise click.ClickException(str(e)) from e
        except Exception as e:
            raise e


@cli.command("upload")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--compressed", "content_format", flag_value="compressed", default=True, type=str)
@click.option("--raw", "content_format", flag_value="raw", type=str)
@click.option("--verbose", "-v", "verbose", is_flag=True)
@click.option("--debug", "debug", is_flag=True)
@click.option("--dry-run", "dry_run", is_flag=True)
@click.option("--silent", "silent", is_flag=True)
@click.pass_obj
def upload_to_server(
    app_ctx: AppContext,
    content_type: ContentType,
    content_format: ContentFormat,
    verbose: bool,
    debug: bool,
    dry_run: bool,
    silent: bool,
):
    client = RsyncClient.from_config(
        app_ctx.config,
        console=app_ctx.console,
        direction="upload",
        content_format=content_format,
        content_type=content_type,
    )
    try:
        if verbose:
            client.console.print(f"src: {client.src.render()}\ndest: {client.dest.render()}")
        content_to_sync = client.get_new_files(debug=debug)
        # TODO: make table transient
        table = Table(
            title=f"{client.content_format.capitalize()} {client.content_type.capitalize()}s found in src not on server",
            show_lines=True,
        )
        table.add_column("movie_name", style="magenta")
        table.add_column("file_name", style="cyan")
        table.add_column("changes_detected", style="yellow")
        table.add_column("file_size", style="purple")

        table_data = []
        for movie_title, file_info in content_to_sync.items():
            for file_name, changes in file_info.items():
                table_data.append([movie_title, file_name, changes.description, changes.size])

        if len(table_data) == 0:
            client.console.print(
                f"No {client.content_format} {client.content_type} in src not on dest"
            )
            return

        sorted_table_data = sorted(table_data, key=lambda x: (x[0], x[2]))

        for row in sorted_table_data:
            formatted_row = [Text(x) for x in row]
            table.add_row(*formatted_row)

        client.console.print(table)

        match content_type:
            case "movie":
                selected = CheckboxPrompt(
                    message="Select titles to sync",
                    choices=list(content_to_sync.keys()),
                    instruction="Use space to select, enter to confirm.",
                    vi_mode=True,
                ).execute()
                for folder_name in selected:
                    progress = RsyncProgressTracker(
                        title_name=folder_name, direction=client.direction
                    )
                    if not silent:
                        with RsyncRender(
                            title_name=folder_name,
                            direction=client.direction,
                            console=client.console,
                        ) as render:
                            for curr_state in progress.track(
                                client.sync_subdir(folder_name, debug=debug, dry_run=dry_run),
                                verbose=verbose,
                            ):
                                render.update(curr_state)
                    else:
                        client.sync_subdir(folder_name, debug=debug, dry_run=dry_run)

            case "tv":
                selected_show = ListPrompt(
                    message="Select show to sync:",
                    choices=list(content_to_sync.keys()),
                    instruction="Use space to select, enter to confirm",
                    vi_mode=True,
                ).execute()
                show_info = content_to_sync[selected_show]
                selected_episodes = CheckboxPrompt(
                    message="Select episodes to sync:",
                    choices=list(show_info.keys()),
                    instruction="Use space to select, enter to confirm",
                    vi_mode=True,
                ).execute()

                selected = [Path(f"{selected_show}/{episode}") for episode in selected_episodes]
                for title_path in selected:
                    progress = RsyncProgressTracker(
                        title_name=str(title_path), direction=client.direction
                    )
                    if not silent:
                        with RsyncRender(
                            title_name=str(title_path),
                            direction=client.direction,
                            console=client.console,
                        ) as render:
                            for curr_state in progress.track(
                                client.sync_file(
                                    rel_file_path=title_path, debug=debug, dry_run=dry_run
                                ),
                                verbose=verbose,
                            ):
                                render.update(curr_state)
                    else:
                        client.sync_file(rel_file_path=title_path, debug=debug, dry_run=dry_run)

    except AssertionError as e:
        raise e
    except Exception as e:
        raise e


@cli.command("download")
@click.option("--movie", "content_type", flag_value="movie", default=True, type=str)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--compressed", "content_format", flag_value="compressed", default=True, type=str)
@click.option("--raw", "content_format", flag_value="raw", type=str)
@click.option("--verbose", "-v", "verbose", is_flag=True)
@click.option("--debug", "debug", is_flag=True)
@click.option("--dry-run", "dry_run", is_flag=True)
@click.option("--silent", "silent", is_flag=True)
@click.pass_obj
def download_from_server(
    app_ctx: AppContext,
    content_type: ContentType,
    content_format: ContentFormat,
    verbose: bool = False,
    debug: bool = False,
    dry_run: bool = False,
    silent: bool = False,
):
    client = RsyncClient.from_config(
        app_ctx.config,
        console=app_ctx.console,
        direction="download",
        content_format=content_format,
        content_type=content_type,
    )
    try:
        if verbose:
            client.console.print(f"src: {client.src.render()}\ndest: {client.dest.render()}")
        content_to_sync = client.get_new_files(debug=debug)
        # TODO: make table transient
        table = Table(
            title=f"{client.content_format.capitalize()} {client.content_type.capitalize()}s found in src not on server",
            show_lines=True,
        )
        table.add_column("movie_name", style="magenta")
        table.add_column("file_name", style="cyan")
        table.add_column("changes_detected", style="yellow")
        table.add_column("file_size", style="purple")

        table_data = []
        for movie_title, file_info in content_to_sync.items():
            for file_name, changes in file_info.items():
                table_data.append([movie_title, file_name, changes.description, changes.size])

        if len(table_data) == 0:
            client.console.print(
                f"No {client.content_format} {client.content_type} in src not on dest"
            )
            return

        sorted_table_data = sorted(table_data, key=lambda x: (x[0], x[2]))

        for row in sorted_table_data:
            formatted_row = [Text(x) for x in row]
            table.add_row(*formatted_row)

        client.console.print(table)

        match content_type:
            case "movie":
                selected = CheckboxPrompt(
                    message="Select movies to sync:",
                    choices=list(content_to_sync.keys()),
                    instruction="Use space to select, enter to confirm.",
                    vi_mode=True,
                ).execute()
                for title_path in selected:
                    progress = RsyncProgressTracker(
                        title_name=title_path, direction=client.direction
                    )
                    if not silent:
                        with RsyncRender(
                            title_name=title_path,
                            direction=client.direction,
                            console=client.console,
                        ) as render:
                            for curr_state in progress.track(
                                client.sync_subdir(subdir=title_path, debug=debug, dry_run=dry_run),
                                verbose=verbose,
                            ):
                                render.update(curr_state)
                    else:
                        client.sync_subdir(subdir=title_path, debug=debug, dry_run=dry_run)

            case "tv":
                selected_show = ListPrompt(
                    message="Select show to sync:",
                    choices=list(content_to_sync.keys()),
                    instruction="Use space to select, enter to confirm",
                    vi_mode=True,
                ).execute()
                show_info = content_to_sync[selected_show]
                selected_episodes = CheckboxPrompt(
                    message="Select episodes to sync:",
                    choices=list(show_info.keys()),
                    instruction="Use space to select, enter to confirm",
                    vi_mode=True,
                ).execute()

                selected = [Path(f"{selected_show}/{episode}") for episode in selected_episodes]
                for title_path in selected:
                    progress = RsyncProgressTracker(
                        title_name=str(title_path), direction=client.direction
                    )
                    if not silent:
                        with RsyncRender(
                            title_name=str(title_path),
                            direction=client.direction,
                            console=client.console,
                        ) as render:
                            for curr_state in progress.track(
                                client.sync_file(
                                    rel_file_path=title_path, debug=debug, dry_run=dry_run
                                ),
                                verbose=verbose,
                            ):
                                render.update(curr_state)
                    else:
                        client.sync_file(rel_file_path=title_path, debug=debug, dry_run=dry_run)
    except InterruptedError as e:
        raise click.ClickException(str(e)) from e

    except AssertionError as e:
        raise e
    except Exception as e:
        raise e


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
