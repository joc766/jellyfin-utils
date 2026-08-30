import shutil

import click
from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from rich.table import Table

from media_tools.cli.config import AppContext
from media_tools.core.datatypes import ContentFormat, ContentType
from media_tools.rsync_tool.client import RsyncClient
from media_tools.sftp_tool.client import JellyfinSFTPClient, get_imdb_id


@click.command()
@click.pass_obj
def find_missing_raw(app_ctx: AppContext):
    sftp_client = JellyfinSFTPClient.from_config(app_ctx.config)
    console = app_ctx.console
    missing_table = Table(title="Compressed movies with no raw backup on server")
    missing_table.add_column("movie_name")
    for movie_name in sorted(sftp_client.find_missing_raw_movies()):
        missing_table.add_row(movie_name)
    console.print(missing_table, markup=False)


@click.command()
@click.pass_obj
def find_missing_compressed(app_ctx: AppContext):
    sftp_client = JellyfinSFTPClient.from_config(app_ctx.config)
    console = app_ctx.console
    missing_table = Table(title="Raw movies with no compressed version on server")
    missing_table.add_column("movie_name")
    for movie_name in sorted(sftp_client.find_missing_compressed_movies()):
        missing_table.add_row(movie_name)
    console.print(missing_table)


# TODO: remove .DS_Store files too
# TODO: also show option to remove episodes, not just high-level folder
@click.command()
@click.option("--raw", "content_format", flag_value="raw", type=str, default=True)
@click.option("--compressed", "content_format", flag_value="compressed", type=str)
@click.option("--movie", "content_type", flag_value="movie", type=str, default=True)
@click.option("--tv", "content_type", flag_value="tv", type=str)
@click.option("--show", "content_type", flag_value="show", type=str)
@click.pass_obj
def safe_remove(app_ctx: AppContext, content_format: ContentFormat, content_type: ContentType):
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
            message=f"Select which titles you would like to remove from {local_path}",
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
