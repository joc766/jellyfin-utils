from pathlib import Path
from typing import get_args

import click
from InquirerPy.base.control import Choice
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.rawlist import RawlistPrompt

from media_tools.cli.config import AppContext
from media_tools.omdb_tool.organize_files import (
    MovieTitleOptions,
    OmdbClient,
    TvTitleOptions,
    format_size_human,
    organize_movie_title,
    organize_tv_title,
)


# TODO: edge case: when title name is the same, movie got deleted??
@click.command("organize")
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
