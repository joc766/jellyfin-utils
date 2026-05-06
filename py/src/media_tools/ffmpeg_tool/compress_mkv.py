from pathlib import Path

from rich.console import Console

from .client import FFmpegClient
from .progress_tracker import FFmpegProgressTracker

console = Console(stderr=True)


# TODO: add tv vs movie options and handle proper output dir
def compress_mkv(
    input_path: Path,
    source_type: str,
    output_path: Path | None = None,
    overwrite: bool = False,
):
    try:
        client = FFmpegClient(input_path, source_type, output_path=output_path, overwrite=overwrite)
    except FileExistsError as e:
        console.print(f"ERROR: {e}", style="bold red")
        exit(1)
    except Exception as e:
        raise (e)

    input_duration = client.get_ffprobe_duration()

    progress_tracker = FFmpegProgressTracker(input_duration)
    print("Compressing with FFmpeg...")
    try:
        for line in client.start_compress_mkv():
            progress_tracker.handle_line(line)
    except InterruptedError as e:
        progress_tracker.stop_progress()
        console.print(e, style="bold blue")
    finally:
        if not progress_tracker.stopped:
            progress_tracker.stop_progress()
