from pathlib import Path
from typing import get_args

import click
from InquirerPy.base.control import Choice
from InquirerPy.prompts.checkbox import CheckboxPrompt
from InquirerPy.prompts.list import ListPrompt

from media_tools.cli.config import AppContext
from media_tools.core.datatypes import ContentType, DiscType
from media_tools.db.connection import create_new_request
from media_tools.ffmpeg_tool.compress_mkv import compress_mkv
from media_tools.ffmpeg_tool.models import Libx264Preset, Libx264Tune


@click.command("compress")
@click.argument("content_type", type=click.Choice(get_args(ContentType)), default="movie")
@click.argument("disc_type", type=click.Choice(get_args(DiscType)), default="dvd")
@click.option("--overwrite", "-f", "overwrite", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--single-audio", "single_audio", is_flag=True)
@click.option("--preserve-surround", "preserve_surround", is_flag=True)
@click.option("--detect-crop", "detect_crop", is_flag=True)
@click.option("--height", "height", type=int, default=None)
@click.option("--crf", "crf", type=int, default=None)
@click.option("--preset", "preset", type=click.Choice(get_args(Libx264Preset)), default="slow")
@click.option("--tune", "tune", type=click.Choice(get_args(Libx264Tune)), default=None)
@click.option("--dry-run", "dry_run", is_flag=True)
@click.option("--silent", "silent", is_flag=True)
@click.pass_obj
def compress_mkv_cmd(
    app_ctx: AppContext,
    disc_type: DiscType,
    content_type: ContentType,
    overwrite: bool,
    verbose: bool = False,
    preserve_surround: bool = False,
    detect_crop: bool = False,
    single_audio: bool = False,
    height: int | None = None,
    crf: int | None = None,
    preset: Libx264Preset = "slow",
    tune: Libx264Tune = None,
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
                detect_crop=detect_crop,
                height=height,
                crf=crf,
                preset=preset,
                tune=tune,
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
