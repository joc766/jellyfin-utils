from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from rich.console import Console

from .client import MakeMKVClient
from .models import MakeMKVDiscInfo, MakeMKVTitleInfo
from .progress import MakeMKVProgressTracker
from .render import MakeMKVProgressRenderer


def prompt_for_titles(disc_info: MakeMKVDiscInfo) -> list[MakeMKVTitleInfo]:
    prompt = CheckboxPrompt(
        message="Select titles to rip:",
        choices=[
            Choice(title.title_id, name=f"{title.title_name} (duration: {title.duration})")
            for title in disc_info.titles.values()
        ],
        vi_mode=True,
        transformer=lambda result: f"{len(result)} title{'s' if len(result) > 1 else ''} selected",
    )
    # prevents message + transformer from displaying after execution
    prompt.application.erase_when_done = True
    selected_titles = prompt.execute()
    titles_to_rip: list[MakeMKVTitleInfo] = [
        disc_info.titles[title_id] for title_id in selected_titles
    ]
    return titles_to_rip


# TODO: add dry run option for easier testing
# TODO: Handle cleaning file names to proper directory names
def rip_disk(
    client: MakeMKVClient,
    verbose: bool = False,
    debug: bool = False,
    console: Console | None = None,
):

    if console is None:
        console = Console()

    progress_tracker = MakeMKVProgressTracker()
    with MakeMKVProgressRenderer(console=console) as renderer:
        progress_tracker.update_status(
            "Running [repr.filename]makemkvcon info[/repr.filename] (drive info)"
        )
        for line in client.extract_drive_name():
            curr_state = progress_tracker.handle_line(line)
            renderer.update(curr_state)

        progress_tracker.update_status(
            "Running [repr.filename]makemkvcon info[/repr.filename] (disc info)"
        )
        for line in client.extract_disc_info():
            curr_state = progress_tracker.handle_line(line)
            renderer.update(curr_state)

        assert client.disc_info is not None
        renderer.suspend()
        client.check_existing_mkvs()
        titles_to_rip = prompt_for_titles(client.disc_info)

        progress_tracker.update_status("Running [repr.filename]makemkvcon mkv[/repr.filename]")
        renderer.resume()
        for i, title in enumerate(titles_to_rip):
            progress_tracker.update_status(
                f"Ripping {title.title_name} [dim][{i + 1}/{len(titles_to_rip)}][/dim]"
            )
            for line in client.run_makemkv(title_id=title.title_id, verbose=verbose, debug=debug):
                curr_state = progress_tracker.handle_line(line)
                renderer.update(curr_state)
