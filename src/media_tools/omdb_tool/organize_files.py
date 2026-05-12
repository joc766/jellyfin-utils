import os
from pathlib import Path

import requests

OMDB_BASE_URL = "https://omdbapi.com"
OMDB_API_KEY = os.getenv("OMDB_API_KEY")


class MissingCredentialsError(Exception):
    """Raised when OMBD API Key not provided."""

    pass


def get_title(imdb_id: str) -> str:
    if OMDB_API_KEY is None:
        raise MissingCredentialsError("OMDB_API_KEY cannot be None.")
    req_url = f"{OMDB_BASE_URL}?i={imdb_id}&apikey={OMDB_API_KEY}"
    response = requests.get(req_url)
    if response.status_code == 200:
        response_body = response.json()
        omdb_name: str = response_body["Title"].replace(":", "-")
        omdb_year: str = response_body["Year"]

        title_name = f"{omdb_name} ({omdb_year}) [imdbid-{imdb_id}]"
    else:
        raise requests.HTTPError("Request failed.")

    if title_name is not None:
        return title_name
    else:
        raise KeyError("Title name could not be produced.")


def rename_movie(movie_path: Path, imdb_id: str) -> Path:
    if not movie_path.exists():
        raise FileNotFoundError(f"{movie_path} does not exist")
    if not movie_path.is_file():
        raise ValueError("[movie_path] must be a file, not a directory")

    parent_path = movie_path.parent
    title = get_title(imdb_id)
    new_movie_file_name = f"{title}{movie_path.suffix}"
    os.rename(movie_path, parent_path / new_movie_file_name)
    new_parent_path = parent_path.parent / title
    os.rename(parent_path, new_parent_path)

    new_title = new_parent_path / new_movie_file_name
    return new_title
