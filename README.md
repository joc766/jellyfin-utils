# media-tools

CLI for ripping, organizing, compressing, and syncing media between local storage and a Jellyfin host.

## Install

```bash
python -m pip install -e .
```

(Optional dev extras)

```bash
python -m pip install -e ".[dev]"
```

## Quick Start

1. Create `~/.config/media-tools/.env`
2. Add:

```dotenv
LOCAL_BASE=/Volumes/media
JELLYFIN_BASE=/srv/jellyfin/media
JELLYFIN_USER=media
JELLYFIN_HOST=jellyfin.local
OMDB_API_KEY=your_key_here
```

3. Run:

```bash
media-tools rip --movie
```

Custom env file:

```bash
media-tools --env-file /path/to/.env rip --movie
```

## Required Env Vars

- `LOCAL_BASE`: local media root
- `JELLYFIN_BASE`: remote media root on Jellyfin host
- `JELLYFIN_USER`: SSH username for Jellyfin host
- `JELLYFIN_HOST`: SSH host/address
- `OMDB_API_KEY`: OMDb API key (used by `organize`)

## Commands

Global option (all commands):

- `--env-file PATH`: load config from env file (default: `~/.config/media-tools/.env`)

### `organize`

Rename a local raw folder using title metadata from IMDb/OMDb.

```bash
media-tools organize [--movie | --show] <imdb_id>
```

Options:

- `--movie` (default): organize under movie raw flow
- `--show`: organize under show raw flow

Args:

- `<imdb_id>`: IMDb ID (example: `tt0111161`)

### `rip`

Rip disc content to local raw storage.

```bash
media-tools rip [--movie | --tv] [-v|--verbose] [--debug]
```

Options:

- `--movie` (default): output to `raw/movie/`
- `--tv`: output to `raw/tv/`
- `-v, --verbose`: verbose rip output
- `--debug`: debug mode

### `compress`

Compress a selected raw file into compressed storage.

```bash
media-tools compress [--dvd | --bd] [--movie | --tv] [-f|--overwrite] [-v|--verbose]
```

Options:

- `-d, --dvd` (default): DVD compression profile
- `-b, --bd`: Blu-ray compression profile
- `--movie` (default): read `raw/movie/`, write `compressed/movie/`
- `--tv`: read `raw/tv/`, write `compressed/tv/`
- `-f, --overwrite`: overwrite existing output
- `-v, --verbose`: verbose ffmpeg output

### `upload`

Interactive rsync upload from local storage to Jellyfin host.

```bash
media-tools upload [--movie | --show] [--compressed | --raw] [-v|--verbose]
```

Options:

- `--movie` (default): movie content path
- `--show`: show content path
- `--compressed` (default): sync compressed media
- `--raw`: sync raw media
- `-v, --verbose`: verbose rsync output

### `download`

Interactive rsync download from Jellyfin host to local storage.

```bash
media-tools download [--movie | --show] [--compressed | --raw] [-v|--verbose] [--debug]
```

Options:

- `--movie` (default): movie content path
- `--show`: show content path
- `--compressed` (default): sync compressed media
- `--raw`: sync raw media
- `-v, --verbose`: verbose rsync output
- `--debug`: debug sync mode

### `find-missing-raw`

List compressed movies on server that have no raw backup on server.

```bash
media-tools find-missing-raw
```

Options: none

### `find-missing-compressed`

List raw movies on server that have no compressed version on server.

```bash
media-tools find-missing-compressed
```

Options: none

## Expected Local Layout

- `raw/movie/`
- `raw/tv/`
- `compressed/movie/`
- `compressed/tv/`

## Notes

- Several commands are interactive (folder/file selection, sync choices).
- Required tools on `PATH`: MakeMKV, FFmpeg, rsync.
- Current CLI uses both `--tv` and `--show` depending on command; docs reflect current behavior.
