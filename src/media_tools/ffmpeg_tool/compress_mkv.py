from .client import FFmpegClient
from .progress import FFmpegProgressTracker


# TODO: add dry-run parameter for easier testing and planning
def compress_mkv(
    client: FFmpegClient,
    overwrite: bool = False,
    verbose: bool = False,
):
    ffprobe_info = client.get_ffprobe_info()

    progress = FFmpegProgressTracker(ffprobe_info["duration"])
    print("Compressing with FFmpeg...")
    try:
        # not the most sensible to send the field_order back to the client
        if ffprobe_info["field_order"] != "progressive":
            deinterlace = True
        else:
            deinterlace = False
        for line in client.start_compress_mkv(
            overwrite=overwrite, deinterlace=deinterlace, verbose=verbose
        ):
            progress.handle_line(line)
    finally:
        if not progress.stopped:
            progress.stop_progress()
