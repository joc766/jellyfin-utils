CREATE TABLE IF NOT EXISTS request (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,

    cli_cmd TEXT NOT NULL,
    cli_params TEXT CHECK (json_valid(cli_params)),
    exc_cmd TEXT NOT NULL,
    pid INTEGER,
    parent_pid INTEGER,
    start_time TEXT,
    end_time TEXT,
    duration REAL,

    exit_code INTEGER,
    err_msg TEXT
);

INSERT INTO sqlite_sequence (name, seq)
VALUES ('requests', 999);
