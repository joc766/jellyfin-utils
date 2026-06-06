import os
from pathlib import Path
from typing import Literal

import requests

TvTitleOptions = Literal["episode", "extra", "ignore"]
MovieTitleOptions = Literal["main feature", "extra", "trailer", "ignore"]


class OmdbClient:
    OMDB_BASE_URL = "https://omdbapi.com"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_title(self, imdb_id: str) -> tuple[str, str]:
        req_url = f"{self.OMDB_BASE_URL}?i={imdb_id}&apikey={self.api_key}"
        response = requests.get(req_url)
        try:
            if response.status_code == 200:
                response_body = response.json()
                try:
                    omdb_title: str = response_body["Title"].replace(":", "-")
                except KeyError as e:
                    raise KeyError("'Title' missing from OMDB response.") from e
                try:
                    omdb_year: str = response_body["Year"]
                except KeyError as e:
                    raise KeyError("'Year' missing from OMDB response.") from e
            else:
                raise requests.HTTPError(
                    f"OMDB Request failed. Response Code {response.status_code}. API key {self.api_key}"
                )
        except Exception as e:
            raise e

        return omdb_title, omdb_year


def format_full_title(omdb_title: str, omdb_year: str, imdb_id: str):
    return f"{omdb_title} ({omdb_year}) [imdbid-{imdb_id}]"


def format_size_human(size_bytes: float) -> str | None:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024


def organize_movie_title(
    movie_content_base: Path,
    title_path: Path,
    title_type: MovieTitleOptions,
    omdb_title: str,
    omdb_year: str,
    imdb_id: str,
):
    title_name = format_full_title(omdb_title, omdb_year, imdb_id)
    title_dest_folder = movie_content_base / title_name

    title_dest_folder.mkdir(exist_ok=True)

    match title_type:
        case "main feature":
            new_path = title_dest_folder / f"{title_name}{title_path.suffix}"
            if new_path.exists():
                raise Exception(f"Destionation path {new_path} already exists!")
            else:
                title_path.rename(new_path)
        case "extra":
            extras_path = title_dest_folder / "extras"
            extras_path.mkdir(exist_ok=True)
            new_path = extras_path / title_path.name
            title_path.rename(new_path)
        case "trailer":
            new_path = title_dest_folder / f"trailer{title_path.suffix}"
            title_path.rename(new_path)
        case "ignore":
            pass


def organize_tv_title(
    tv_content_base: Path,
    title_path: Path,
    title_type: TvTitleOptions,
    omdb_title: str,
    omdb_year: str,
    imdb_id: str,
    season: str,
    episode: str,
):
    # TODO: try verifying episode duration to suggest match automatically
    match title_type:
        case "episode":
            episode_id = f"S{season}E{episode}"
            title_name = format_full_title(omdb_title, omdb_year, imdb_id)
            title_dest_folder = tv_content_base / title_name

            title_dest_folder.mkdir(exist_ok=True)
            season_folder = title_dest_folder / f"Season {season}"
            season_folder.mkdir(exist_ok=True)
            new_title_path = season_folder / f"{omdb_title} {episode_id}{title_path.suffix}"
            if new_title_path.exists():
                raise ValueError(f"New title path ('{new_title_path}') already exists")
            else:
                title_path.rename(new_title_path)
        case "ignore":
            pass


def organize_movie_file(title_path, omdb_title, omdb_year, imdb_id):
    title = format_full_title(omdb_title, omdb_year, imdb_id)
    parent_path = title_path.parent
    new_movie_file_name = f"{title}{title_path.suffix}"
    os.rename(title_path, parent_path / new_movie_file_name)
    new_parent_path = parent_path.parent / title
    os.rename(parent_path, new_parent_path)
