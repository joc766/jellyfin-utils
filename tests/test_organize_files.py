import os
from pathlib import Path

import pytest

from media_tools.cli import load_config
from media_tools.omdb_tool import (
    OmdbClient,
    format_full_title,
    organize_movie_title,
    organize_tv_title,
)


@pytest.mark.integration
def test_omdb_client():
    api_key = os.environ.get("OMDB_API_KEY")
    if api_key is None:
        raise ValueError("Must set environment variable for OMDB_API_KEY")
    client = OmdbClient(api_key)
    imdb_id = "tt1375666"
    omdb_title, omdb_year = client.get_title(imdb_id)

    assert omdb_title == "Inception"
    assert omdb_year == "2010"

    full_title = format_full_title(omdb_title, omdb_year, imdb_id)
    assert full_title == "Inception (2010) [imdbid-tt1375666]"


@pytest.mark.integration
def test_organize_movie(tmp_path: Path):
    api_key = os.environ.get("OMDB_API_KEY")
    if api_key is None:
        raise ValueError("Must set environment variable for OMDB_API_KEY")
    client = OmdbClient(api_key)
    imdb_id = "tt1375666"
    omdb_title, omdb_year = client.get_title(imdb_id)

    dummy_subdir = tmp_path / "test_dir"
    dummy_subdir.mkdir()
    dummy_movie_path = dummy_subdir / "movie.mp4"
    dummy_movie_path.touch()

    full_title = format_full_title(omdb_title, omdb_year, imdb_id)

    correct_result_path = tmp_path / full_title
    assert not correct_result_path.exists()

    organize_movie_title(tmp_path, dummy_movie_path, "main feature", omdb_title, omdb_year, imdb_id)

    result_file_path = correct_result_path / f"{full_title}.mp4"
    assert correct_result_path.exists()
    assert result_file_path.exists()


@pytest.mark.integration
def test_organize_tv(tmp_path: Path):
    api_key = os.environ.get("OMDB_API_KEY")
    if api_key is None:
        raise ValueError("Must set environment variable for OMDB_API_KEY")
    client = OmdbClient(api_key)
    imdb_id = "tt3032476"
    omdb_title, omdb_year = client.get_title(imdb_id)

    full_title = format_full_title(omdb_title, omdb_year, imdb_id)

    correct_result_path = tmp_path / full_title / "Season 01"
    assert not correct_result_path.exists()

    dummy_subdir = tmp_path / "test_dir"
    dummy_subdir.mkdir()
    dummy_tv_episode_1_path = dummy_subdir / "episode1.mp4"
    dummy_tv_episode_1_path.touch()
    assert dummy_tv_episode_1_path.exists()

    dummy_tv_episode_2_path = dummy_subdir / "episode2.mp4"
    dummy_tv_episode_2_path.touch()
    assert dummy_tv_episode_2_path.exists()

    organize_tv_title(
        tmp_path, dummy_tv_episode_1_path, "episode", omdb_title, omdb_year, imdb_id, "01", "01"
    )
    assert not dummy_tv_episode_1_path.exists()
    assert correct_result_path.exists()

    organize_tv_title(
        tmp_path, dummy_tv_episode_2_path, "episode", omdb_title, omdb_year, imdb_id, "01", "02"
    )
    assert not dummy_tv_episode_2_path.exists()
    assert len(list(correct_result_path.iterdir())) == 2
