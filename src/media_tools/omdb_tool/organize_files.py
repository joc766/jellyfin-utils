import os
from pathlib import Path

import requests
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.rawlist import RawlistPrompt


class OmdbClient:
    OMDB_BASE_URL = "https://omdbapi.com"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.title = None

    def get_title(self, imdb_id: str) -> str:
        # cache title if we've seen it before to prevent duplicate request
        if self.title is None:
            req_url = f"{self.OMDB_BASE_URL}?i={imdb_id}&apikey={self.api_key}"
            response = requests.get(req_url)
            if response.status_code == 200:
                response_body = response.json()
                try:
                    omdb_name: str = response_body["Title"].replace(":", "-")
                    omdb_year: str = response_body["Year"]
                except KeyError as e:
                    raise KeyError(f"OMDB response does not contain field {e}") from e

                title_name = f"{omdb_name} ({omdb_year}) [imdbid-{imdb_id}]"
            else:
                raise requests.HTTPError("Request failed.")

            self.title = title_name
            return title_name
        else:
            return self.title

    def _format_size(self, size_bytes: float) -> str | None:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

    def rename_movie(self, movie_path: Path, imdb_id: str) -> None:
        if not movie_path.exists():
            raise FileNotFoundError(f"{movie_path} does not exist")

        try:
            title = self.get_title(imdb_id)
        except Exception as e:
            raise e
        if movie_path.is_dir():
            content_choices = ["main feature", "extra", "trailer", "ignore"]
            for file in movie_path.iterdir():
                file_size = self._format_size(file.stat().st_size)
                assert file_size is not None
                selected = RawlistPrompt(
                    message=f"Select content type for {file.name} ({file_size})",
                    choices=content_choices,
                    vi_mode=True,
                    transformer=lambda result: f"{result}",
                ).execute()
                if selected == "main feature":
                    os.rename(file, file.parent / f"{title}{file.suffix}")
                elif selected == "extra":
                    extra_name = InputPrompt(
                        message="Enter title for extra: ", vi_mode=True
                    ).execute()
                    (file.parent / "extras").mkdir(exist_ok=True)
                    os.rename(file, file.parent / "extras" / f"{extra_name}{file.suffix}")
                elif selected == "trailer":
                    os.rename(file, file.parent / f"trailer{file.suffix}")
                else:
                    continue
            os.rename(movie_path, movie_path.parent / title)

        else:
            parent_path = movie_path.parent
            new_movie_file_name = f"{title}{movie_path.suffix}"
            os.rename(movie_path, parent_path / new_movie_file_name)
            new_parent_path = parent_path.parent / title
            os.rename(parent_path, new_parent_path)
