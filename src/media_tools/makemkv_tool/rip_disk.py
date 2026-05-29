from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from rich.console import Console

from media_tools.makemkv_tool.progress import MakeMKVProgressTracker

from .client import MakeMKVClient
from .models import MakeMKVDiscInfo, MakeMKVTitleInfo


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

    with MakeMKVProgressTracker(console=console) as mkv_progress:
        mkv_progress.set_status("Extracting drive info...")
        for line in client.extract_drive_name():
            mkv_progress.handle_line(line)

        mkv_progress.set_status("Extracting disc info...")
        for line in client.extract_disc_info():
            mkv_progress.handle_line(line)

        assert client.disc_info is not None
        mkv_progress.suspend()
        client.check_existing_mkvs()
        titles_to_rip = prompt_for_titles(client.disc_info)

        mkv_progress.set_status("Beginning makemkvcon...")
        mkv_progress.resume()
        for i, title in enumerate(titles_to_rip):
            mkv_progress.set_status(f"Ripping {title.title_name} ({i + 1}/{len(titles_to_rip)})")
            for line in client.run_makemkv(title_id=title.title_id, verbose=verbose, debug=debug):
                mkv_progress.handle_line(line)
