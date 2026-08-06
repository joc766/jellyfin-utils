from pathlib import Path

from rich.console import Console

from media_tools.ffmpeg_tool.client import FFmpegClient
from media_tools.ffmpeg_tool.progress import FFmpegProgressRender, FFmpegProgressTracker
from media_tools.ffmpeg_tool.utils import probe_audios, probe_video


# TODO: add dry-run parameter for easier testing and planning
def compress_mkv(
    output_base: Path,
    input_path: Path,
    input_base: Path,
    source_type: str,
    request_id: int | None = None,
    overwrite: bool = False,
    verbose: bool = False,
    single_audio: bool = False,
    preserve_surround_track: bool = False,
    height: int | None = None,
    crf: int | None = None,
    preset: str = "slow",
    dry_run: bool = False,
    silent: bool = False,
    console: Console | None = None,
):
    client = FFmpegClient(input_path=input_path, console=console, source_type=source_type)
    video_info = probe_video(input_path)
    # TODO: use selected audio instead of first
    audio_info = probe_audios(input_path)[0]
    duration = max(video_info.tags.duration_eng, audio_info.tags.duration_eng)
    field_order = video_info.field_order
    progress = FFmpegProgressTracker()
    deinterlace = field_order != "progressive"

    output_tag = f"{height}p" if height is not None else f"{video_info.height}p"
    output_path: Path = (
        output_base / f"{input_path.relative_to(input_base).with_suffix('')} - {output_tag}"
    ).with_suffix(".mp4")
    output_path.parent.mkdir(exist_ok=True, parents=True)

    stdout_lines = client.start_compress_mkv(
        output_path=output_path,
        request_id=request_id,
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
    try:
        if silent:
            for _ in stdout_lines:
                pass
        else:
            with FFmpegProgressRender(client.input_path.stem, duration.seconds) as render:
                for line in stdout_lines:
                    curr_state = progress.handle_line(line)
                    render.update(curr_state)
    finally:
        stdout_lines.close()
