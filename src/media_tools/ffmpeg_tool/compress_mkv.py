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
    silent: bool = False,
):
    video_info = client.probe_video()
    # TODO: use selected audio instead of first
    audio_info = client.probe_audios()[0]
    duration = max(video_info.tags.duration_eng, audio_info.tags.duration_eng)
    field_order = video_info.field_order
    progress = FFmpegProgressTracker()
    deinterlace = field_order != "progressive"

    stdout_lines = client.start_compress_mkv(
        overwrite=overwrite,
        deinterlace=deinterlace,
        verbose=verbose,
        single_audio=single_audio,
        preserve_surround_track=preserve_surround_track,
        height=height,
        crf=crf,
        preset=preset,
        dry_run=dry_run,
    )
    if silent:
        for _ in stdout_lines:
            pass
    else:
        with FFmpegProgressRender(client.input_path.stem, duration.seconds) as render:
            for line in stdout_lines:
                curr_state = progress.handle_line(line)
                render.update(curr_state)
