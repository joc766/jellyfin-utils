from pathlib import Path
from typing import get_args

import click
from InquirerPy.prompts.checkbox import CheckboxPrompt
from InquirerPy.prompts.list import ListPrompt
from rich.table import Table
from rich.text import Text

from media_tools.cli.config import AppContext
from media_tools.core.datatypes import ContentFormat, ContentType
from media_tools.rsync_tool.client import RsyncClient
from media_tools.rsync_tool.models import TransferDirection
from media_tools.rsync_tool.progress import RsyncProgressTracker
from media_tools.rsync_tool.render import RsyncRender


def sync(
    app_ctx: AppContext,
    direction: TransferDirection,
    content_format: ContentFormat,
    content_type: ContentType,
    verbose: bool,
    debug: bool,
    dry_run: bool,
    silent: bool,
):
    try:
        client = RsyncClient.from_config(
            app_ctx.config,
            console=app_ctx.console,
            direction=direction,
            content_format=content_format,
            content_type=content_type,
        )
        if verbose:
            client.console.print(f"src: {client.src.render()}\ndest: {client.dest.render()}")

        new_files = client.get_new_files(debug=debug)
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
        for movie_title, file_info in new_files.items():
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

        selected_folder = ListPrompt(
            message="Select folder to sync:",
            choices=list(new_files.keys()),
            instruction="Press Enter to select.",
            vi_mode=True,
        ).execute()

        selected_files = CheckboxPrompt(
            message="Select files to sync:",
            choices=list(new_files[selected_folder].keys()),
            instruction="Use Space to select, enter to confirm",
            vi_mode=True,
        ).execute()

        for file in selected_files:
            rel_file_path = Path(selected_folder) / file
            progress = RsyncProgressTracker(title_name=file, direction=client.direction)
            if not silent:
                with RsyncRender(
                    title_name=file,
                    direction=client.direction,
                    console=client.console,
                ) as render:
                    for curr_state in progress.track(
                        client.sync_file(rel_file_path, debug=debug, dry_run=dry_run),
                        verbose=verbose,
                    ):
                        render.update(curr_state)
            else:
                client.sync_file(rel_file_path, debug=debug, dry_run=dry_run)

    except AssertionError as e:
        raise e
    except (InterruptedError, ConnectionError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise e


def sync_options(func):
    decorators = [
        click.argument("content-format", type=click.Choice(get_args(ContentFormat))),
        click.argument("content-type", type=click.Choice(get_args(ContentType))),
        click.option("--verbose", "-v", "verbose", is_flag=True),
        click.option("--debug", "debug", is_flag=True),
        click.option("--dry-run", "dry_run", is_flag=True),
        click.option("--silent", "silent", is_flag=True),
    ]

    for decorator in reversed(decorators):
        func = decorator(func)

    return func


@click.command()
@sync_options
@click.pass_obj
def upload(app_ctx, **kwargs):
    sync(app_ctx, "upload", **kwargs)


@click.command()
@sync_options
@click.pass_obj
def download(app_ctx, **kwargs):
    sync(app_ctx, "download", **kwargs)
