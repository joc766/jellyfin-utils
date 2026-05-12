import os
from pathlib import Path

from rich.console import Console

from .client import FFmpegClient
from .progress import FFmpegProgressTracker

STORAGE_BASE = Path(os.getenv("STORAGE_BASE", "/Volumes/SanDisk"))
COMPRESSED_STORAGE_BASE = STORAGE_BASE / "compressed"

console = Console(stderr=True)


def make_output_path(
    input_path: Path,
    output_container: str,
    content_type: str,
    output_dir: Path | None = None,
    output_filename: str | None = None,
) -> Path:
    if output_filename is None:
        output_filename = input_path.stem
    else:
        output_filename = "".join(output_filename.split(".")[0:-1])

    if output_dir is None:
        output_dir = COMPRESSED_STORAGE_BASE / content_type / input_path.parent.stem

    output_path = output_dir / f"{output_filename}.{output_container}"

    return output_path


def compress_mkv(
    input_path: Path,
    source_type: str = "DVD",
    content_type: str = "movie",
    output: Path | None = None,
    output_dir: Path | None = None,
    output_filename: str | None = None,
    output_container: str = "mp4",
    overwrite: bool = False,
):
    if output is None:
        output = make_output_path(
            input_path,
            output_container,
            content_type=content_type,
            output_dir=output_dir,
            output_filename=output_filename,
        )

    if output.exists() and not overwrite:
        raise FileExistsError(f"'{output}' already exists and overwrite=False")
    if not output.parent.exists():
        output.parent.mkdir(parents=True)

    try:
        client = FFmpegClient(input_path, source_type)
    except Exception as e:
        raise e

    input_duration = client.get_ffprobe_duration()

    progress = FFmpegProgressTracker(input_duration)
    print("Compressing with FFmpeg...")
    try:
        for line in client.start_compress_mkv(output, overwrite=overwrite):
            progress.handle_line(line)
    except InterruptedError as e:
        progress.stop_progress()
        console.print(e, style="bold blue")
    finally:
        if not progress.stopped:
            progress.stop_progress()
