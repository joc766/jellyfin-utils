import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console


@dataclass(frozen=True)
class AppConfig:
    jellyfin_base: Path
    jellyfin_host: str | None
    jellyfin_user: str | None
    local_base: Path
    omdb_api_key: str


@dataclass(frozen=True)
class AppContext:
    config: AppConfig
    console: Console


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config(dotenv_path: Path | None = None) -> AppConfig:
    if dotenv_path is None:
        home_dir = Path(require_env("HOME"))
        dotenv_path = home_dir / ".config" / "media-tools" / ".env"

    if not dotenv_path.is_file():
        raise FileNotFoundError(f"No .env file found in {str(dotenv_path.parent)}")

    load_dotenv(dotenv_path, override=True)

    local_base = Path(require_env("LOCAL_BASE"))
    if not local_base.exists():
        raise FileNotFoundError(f"local_base {local_base} does not exist")

    return AppConfig(
        local_base=local_base,
        jellyfin_base=Path(require_env("JELLYFIN_BASE")),
        jellyfin_user=os.getenv("JELLYFIN_USER"),
        jellyfin_host=os.getenv("JELLYFIN_HOST"),
        omdb_api_key=require_env("OMDB_API_KEY"),
    )
