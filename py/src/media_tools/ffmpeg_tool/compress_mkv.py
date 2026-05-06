from pathlib import Path

from rich.console import Console
from rich.text import Text

from .client import FFmpegClient
from .progress_tracker import FFmpegProgressTracker

console = Console(stderr=True)


# TODO: add tv vs movie options and handle proper output dir
def compress_mkv(
    input_path: Path,
    source_type: str,
    input_duration: float | None = None,
    output_path: Path | None = None,
    overwrite: bool = False,
):
    try:
        client = FFmpegClient(input_path, source_type, output_path=output_path, overwrite=overwrite)
    except FileExistsError as e:
        text = Text(f"ERROR: {e}", style="bold red")
        console.print(text)
        exit(1)
    except Exception as e:
        raise (e)

    if input_duration is None:
        # TODO: automatically determine duration with ffprobe
        input_duration = 6000.00
        pass

    progress_tracker = FFmpegProgressTracker(input_duration)
    print("Compressing with FFmpeg...")
    for line in client.start_compress_mkv():
        progress_tracker.handle_line(line)
