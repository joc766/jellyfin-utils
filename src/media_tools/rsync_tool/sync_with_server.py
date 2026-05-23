from collections.abc import Iterable

from InquirerPy.prompts.checkbox import CheckboxPrompt
from rich.table import Table
from rich.text import Text

from .client import RsyncClient
from .models import TransferDirection
from .progress import RsyncProgressTracker


def track_progress(
    rsync_lines: Iterable[str], title_name: str, direction: TransferDirection, verbose: bool = False
) -> None:
    progress = RsyncProgressTracker(title_name=title_name, direction=direction)
    progress.initialize()
    try:
        for line in rsync_lines:
            if verbose:
                print(repr(line))
            progress.handle_line(line)
    finally:
        if not progress.stopped:
            progress.stop_progress()


def sync_with_server(
    client: RsyncClient,
    title_name: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Sync the full STORGAGE_BASE with JELLFYIN_BASE"""
    track_progress(
        client.sync(dry_run=dry_run), title_name, direction=client.direction, verbose=verbose
    )


def interactive_sync(client: RsyncClient, verbose: bool = False, debug: bool = False) -> None:
    if verbose:
        client.console.print(f"src: {client.src.render()}\ndest: {client.dest.render()}")
    content_to_sync = client.get_new_files(debug=debug)
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
        client.console.print(f"No {client.content_format} {client.content_type} in src not on dest")
        return

    sorted_table_data = sorted(table_data, key=lambda x: (x[0], x[2]))

    for row in sorted_table_data:
        formatted_row = [Text(x) for x in row]
        table.add_row(*formatted_row)

    client.console.print(table)

    selected = CheckboxPrompt(
        message="Select titles to sync",
        choices=list(content_to_sync.keys()),
        instruction="Use space to select, enter to confirm.",
        vi_mode=True,
    ).execute()

    for folder_name in selected:
        track_progress(
            client.sync_subdir(folder_name, debug=debug),
            title_name=folder_name,
            direction=client.direction,
            verbose=verbose,
        )
