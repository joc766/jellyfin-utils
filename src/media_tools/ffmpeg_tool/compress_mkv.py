from media_tools.ffmpeg_tool.client import FFmpegClient
from media_tools.ffmpeg_tool.progress import FFmpegProgressRender, FFmpegProgressTracker


# TODO: add dry-run parameter for easier testing and planning
def compress_mkv(
    client: FFmpegClient,
    overwrite: bool = False,
    verbose: bool = False,
    single_audio: bool = False,
    preserve_surround_track: bool = False,
    height: int | None = None,
    crf: int | None = None,
    preset: str = "slow",
    dry_run: bool = False,
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
            single_audio=single_audio,
            preserve_surround_track=preserve_surround_track,
            height=height,
            crf=crf,
            preset=preset,
            dry_run=dry_run,
        ):
            curr_state = progress.handle_line(line)
            render.update(curr_state)
