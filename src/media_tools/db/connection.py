import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DB_PATH = Path.home() / ".local" / "share" / "media-tools" / "db.sqlite3"

DT_FORMAT = "%Y-%m-%d %H:%M:%S%f"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_datetime() -> datetime:
    return datetime.now(ZoneInfo("America/New_York"))


def create_new_request(
    cli_cmd: str, cli_params: dict[str, Any], exc_cmd: str, pid: int, db_path: Path | None = None
) -> int:
    with connect(db_path) as conn:
        curr_dt = get_datetime().strftime(DT_FORMAT)
        cursor = conn.execute(
            """
            INSERT INTO request (cli_cmd, cli_params, exc_cmd, start_time, pid)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cli_cmd, json.dumps(cli_params), exc_cmd, curr_dt, pid),
        )
        request_id = cursor.lastrowid
        if request_id is not None:
            return request_id
        else:
            raise ValueError("Error Inserting Row.")


def complete_request(
    request_id: int, exit_code: int, err_msg: str | None = None, db_path: Path | None = None
) -> None:
    end_time = get_datetime().replace(tzinfo=None)
    with connect(db_path) as conn:
        curr_dt = end_time.strftime(DT_FORMAT)
        cursor = conn.execute(
            """
            SELECT start_time FROM request
            WHERE request_id = ?
            """,
            (request_id,),
        )
        start_time_str = cursor.fetchone()[0]
        start_time = datetime.strptime(start_time_str, DT_FORMAT)
        duration = (end_time - start_time).total_seconds()
        conn.execute(
            """
            UPDATE request SET end_time = ?, duration = ?, exit_code = ?, err_msg = ?
            WHERE request_id = ?
            """,
            (curr_dt, duration, exit_code, err_msg, request_id),
        )


def init_db(db_path: Path | None = None) -> None:
    schema_path = Path(__file__).parent / "migrations" / "001_init.sql"
    with connect(db_path) as conn:
        conn.executescript(schema_path.read_text())
