from .client import FFmpegClient
from .progress import FFmpegProgressRender, FFmpegProgressTracker


# TODO: add dry-run parameter for easier testing and planning
def compress_mkv(
    client: FFmpegClient,
    overwrite: bool = False,
    verbose: bool = False,
    preserve_surround_track: bool = False,
):
    ffprobe_info = client.get_ffprobe_info()
    duration = ffprobe_info["duration"]
    field_order = ffprobe_info["field_order"]
    progress = FFmpegProgressTracker()
    deinterlace = field_order != "progressive"
    with FFmpegProgressRender(client.input_path.stem, duration) as render:
        for line in client.start_compress_mkv(
            overwrite=overwrite,
            deinterlace=deinterlace,
            verbose=verbose,
            preserve_surround_track=preserve_surround_track,
        ):
            curr_state = progress.handle_line(line)
            render.update(curr_state)
