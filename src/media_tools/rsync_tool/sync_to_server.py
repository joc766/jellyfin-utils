import os
import re
from collections import defaultdict
from pathlib import Path

from InquirerPy.prompts.checkbox import CheckboxPrompt
from rich import get_console
from rich.table import Table
from rich.text import Text

from .client import RsyncClient
from .progress import RsyncProgressTracker

console = get_console()

STORAGE_BASE = Path(os.getenv("STORAGE_BASE", "/Volumes/SanDisk"))

JELLYFIN_BASENAME = os.getenv("JELLYFIN_BASENAME", "/mnt/storage/jellyfin/")
JELLYFIN_SERVERNAME = os.getenv("JELLYFIN_SERVERNAME", "jackoconnor@192.168.50.2")

INTRO_MSG_PATTERN = re.compile(r"^sending incremental file list$")
SENT_MSG_PATTERN = re.compile(r"^sent .* bytes  received .* bytes .* bytes/sec$")
TOTAL_MSG_PATTERN = re.compile(r"^total size is .*  speedup is.*")
ITEMIZED_PATTERN = re.compile(r"^(?P<prefix>.{11})\s+(?P<path>.+)$")


CHANGES = {
    "s": "size",
    "t": "timestamp",
    "c": "checksum",
    "p": "permissions",
    "o": "owner",
    "g": "group",
}


def get_list_of_files(
    content_type: str = "movie", content_format: str = "compressed"
) -> dict[str, dict]:
    src_path = STORAGE_BASE / content_format / content_type
    dest_path = JELLYFIN_BASENAME + f"{content_format}/" + f"{content_type}/"
    dest_server = JELLYFIN_SERVERNAME
    client = RsyncClient()

    content_to_sync = defaultdict(dict)
    for line in client.start_rsync(
        src_path, dest_server, dest_path, contents_only=True, dry_run=True
    ):
        if (
            not INTRO_MSG_PATTERN.match(line)
            and not SENT_MSG_PATTERN.match(line)
            and not TOTAL_MSG_PATTERN.match(line)
        ):
            if item_match := ITEMIZED_PATTERN.match(line):
                prefix = item_match["prefix"]
                itemized_changes = {
                    "raw_prefix": prefix,
                    "update": prefix[0],
                    "filetype": prefix[1],
                    "changes_raw": prefix[2:],
                    "path": Path(item_match["path"]),
                    "is_created": prefix[2:] == "+++++++++",
                    "changes": dict(zip("cstpoguax", prefix[2:], strict=False)),
                }
                path = itemized_changes["path"]
                if len(str(path).split("/")) != 2:
                    print(f"ignoring {line}")
                else:
                    if itemized_changes["filetype"] == "f":
                        movie_title = str(path.parent)
                        filename = path.name
                        content_to_sync[movie_title][filename] = (
                            "New"
                            if itemized_changes["is_created"]
                            else ",".join(
                                CHANGES[x] for x in itemized_changes["changes"].values() if x != "."
                            )
                        )

    return content_to_sync


def sync_to_server(
    src: Path,
    dest_server: str = JELLYFIN_SERVERNAME,
    content_type: str = "movie",
    content_format: str = "compressed",
    dry_run: bool = False,
    verbose: bool = False,
):
    if not src.exists():
        raise FileNotFoundError(f"src: file or directory {src} does not exist")
    if src.is_file():
        title_name = src.name
    else:
        title_name = src.stem
    client = RsyncClient()
    progress = RsyncProgressTracker(title_name=title_name)

    dest_path = JELLYFIN_BASENAME + f"{content_format}/" + f"{content_type}/"

    try:
        for line in client.start_rsync(
            src, dest_server, dest_path, dry_run=dry_run, contents_only=False
        ):
            if verbose:
                print(repr(line))
            progress.handle_line(line)
    finally:
        if not progress.stopped:
            progress.stop_progress()


def interactive_sync(content_type: str = "movie", content_format: str = "compressed"):
    content_to_sync = get_list_of_files(content_type=content_type, content_format=content_format)
    table = Table(
        title=f"{content_format.capitalize()} {content_type.capitalize()}s found in src not on server",
        show_lines=True,
    )
    table.add_column("movie_name", style="magenta")
    table.add_column("file_name", style="cyan")
    table.add_column("changes_detected", style="yellow")

    table_data = []
    for movie_title, change_dict in content_to_sync.items():
        for file_name, changes in change_dict.items():
            table_data.append([movie_title, file_name, changes])

    sorted_table_data = sorted(table_data, key=lambda x: (x[0], x[2]))

    for row in sorted_table_data:
        formatted_row = [Text(x) for x in row]
        table.add_row(*formatted_row)

    console.print(table)

    selected = CheckboxPrompt(
        message="Select titles to sync",
        choices=list(content_to_sync.keys()),
        instruction="Use space to select, enter to confirm.",
    ).execute()

    for folder_name in selected:
        src_path = STORAGE_BASE / content_format / content_type / folder_name
        sync_to_server(
            src_path,
            content_type=content_type,
            content_format=content_format,
        )
