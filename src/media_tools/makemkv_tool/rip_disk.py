from .client import MakeMKVClient
from .progress import MakeMKVProgressTracker


# TODO: add dry run option for easier testing
# TODO: Handle cleaning file names to proper directory names
def rip_disk(client: MakeMKVClient, verbose: bool = False, debug: bool = False):
    client.console.print("Beginning makemkvcon...")
    titles_to_rip = client.prompt_for_titles()
    for i, title in enumerate(titles_to_rip):
        client.console.print(f"Ripping {title.title_name} ({i + 1}/{len(titles_to_rip)})")
        mkv_progress = MakeMKVProgressTracker()
        try:
            for line in client.start_mkv_process(title_id=title.title_id, debug=debug):
                if verbose:
                    client.console.print(line)
                mkv_progress.handle_line(line)
        finally:
            if not mkv_progress.finished:
                mkv_progress.stop_progress()
