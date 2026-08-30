from pathlib import Path

import click
from InquirerPy.base.control import Choice
from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt
from prompt_toolkit.validation import ValidationError, Validator
from rich.table import Table

from media_tools.cli.config import AppContext
from media_tools.core.datatypes import ContentType
from media_tools.ffmpeg_tool.client import FFmpegClient
from media_tools.ffmpeg_tool.utils import probe_audios


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


@click.command("sample-audios")
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
    audios = probe_audios(client.input_path)
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
