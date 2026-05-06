from .client import FFmpegClient
from .progress_tracker import FFmpegProgressTracker


# TODO: add tv vs movie options and handle proper output dir
def compress_mkv(
    input_path: str,
    source_type: str,
    input_duration: float,
    output_path: str | None = None,
    overwrite: bool = False,
):
    client = FFmpegClient(input_path, source_type, output_path=output_path, overwrite=overwrite)

    progress_tracker = FFmpegProgressTracker(input_duration)
    print("Compressing with FFmpeg...")
    for line in client.start_compress_mkv():
        progress_tracker.handle_line(line)
