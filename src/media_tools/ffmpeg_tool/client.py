import re
import shlex
import signal
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text

from media_tools.db.connection import complete_request, create_new_request


def create_ffmpeg_compress_cmd(
    executable: str,
    source_type: str,
    input_path: Path,
    output_path: Path,
    overwrite: bool = False,
    deinterlace: bool = False,
    single_audio: bool = False,
    crf: int | None = None,
    preset: str = "slow",
    preserve_surround_track: bool = False,
):
    command = [executable]
    if overwrite:
        command.append("-y")
    else:
        command.append("-n")
    if crf is None:
        if source_type == "DVD":
            crf = 20
        else:
            crf = 18
    command.extend(["-nostdin", "-progress", "pipe:1", "-nostats"])
    command.extend(["-i", str(input_path)])
    command.extend(
        [
            "-map_metadata",
            "0",
            "-map_chapters",
            "0",
            "-sn",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            # "0:a:m:language:eng",
        ]
    )
    # TODO: maybe merge single-audio and preserve-surround to a better flag
    if not single_audio:
        command.extend(
            [
                "-map",
                "0:a:0",
            ]
        )
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.1",
        ]
    )
    # command.extend(["-maxrate", "20M", "-bufsize", "20M", "-x264-params", "interlaced=0"])
    command.extend(["-c:a:0", "libfdk_aac", "-ac:a:0", "2", "-ar:a:0", "48000", "-b:a:0", "256k"])
    command.extend(
        ["-filter:a:0", "acompressor=threshold=-20dB:ratio=3,loudnorm=I=-18:TP=-1.5:LRA=10"]
    )
    if not single_audio:
        command.extend(["-c:a:1", "copy" if preserve_surround_track else "libfdk_aac"])
    if not single_audio and not preserve_surround_track:
        command.extend(["-b:a:1", "512k"])
    if not single_audio:
        command.extend(["-disposition:a:1", "0"])
        command.extend(["-metadata:s:a:1", "title=Surround 5.1"])
    command.extend(["-disposition:a:0", "default"])
    command.extend(["-metadata:s:a:0", "title=Stereo AAC"])
    command.extend(["-movflags", "+faststart"])

    deinterlace_filter = "yadif"
    if source_type == "DVD":
        command.extend(["-fflags", "+genpts", "-avoid_negative_ts", "make_zero"])
        scale_filter = "scale=trunc(480*dar/2)*2:480:flags=lanczos,setsar=1,setfield=prog"
        if deinterlace:
            command.extend(["-vf", f"{deinterlace_filter},{scale_filter}"])
        else:
            command.extend(["-vf", scale_filter])
    elif deinterlace:
        command.extend(["-vf", deinterlace_filter])

    command.append(str(output_path))

    return command


class FFmpegClient:
    def __init__(
        self,
        *,
        input_path: Path,
        output_path: Path,
        console: Console | None = None,
        source_type: str = "DVD",
        executable: str = "ffmpeg",
    ):
        self.executable = executable
        self.source_type = source_type
        self.input_path = input_path
        self.output_path = output_path
        self.console = console
        self.ffmpeg_proc = None

        if not self.input_path.exists():
            raise FileNotFoundError(f"input_path {input_path} does not exist.")

        if not self.output_path.parent.exists():
            raise FileNotFoundError(f"output parent dir {output_path.parent} does not exist.")

    def get_ffprobe_info(self) -> dict[str, Any]:
        """Returns the max duration between the first video stream and first audio stream"""
        video_command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream_tags=DURATION-eng",
            "-show_entries",
            "stream=field_order",
            "-of",
            "default=nw=1",
            str(self.input_path),
        ]
        audio_command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream_tags=DURATION-eng",
            "-of",
            "default=nw=1",
            str(self.input_path),
        ]

        # Calculate video duration in seconds
        video_result = subprocess.run(video_command, capture_output=True, text=True)
        assert video_result.stdout is not None
        video_duration_match = re.search(
            "TAG:DURATION-eng=(\\d{2}):(\\d{2}):(\\d{2}.\\d+)", video_result.stdout
        )
        assert video_duration_match is not None
        hours, minutes, seconds = video_duration_match.group(1, 2, 3)
        video_duration = 0.0
        video_duration += int(hours) * 3600
        video_duration += int(minutes) * 60
        video_duration += float(seconds)

        # Calculate audio duration in seconds
        audio_result = subprocess.run(audio_command, bufsize=1, capture_output=True, text=True)
        assert audio_result.stdout is not None
        audio_duration_match = re.search(
            "^TAG:DURATION-eng=(\\d{2}):(\\d{2}):(\\d{2}.\\d+)", audio_result.stdout.rstrip("\n")
        )
        assert audio_duration_match is not None
        hours, minutes, seconds = audio_duration_match.group(1, 2, 3)
        audio_duration = 0.0
        audio_duration += int(hours) * 3600
        audio_duration += int(minutes) * 60
        audio_duration += float(seconds)

        field_order_match = re.search(r"field_order=([a-z]+)", video_result.stdout)
        assert field_order_match is not None
        field_order = field_order_match.group(1)

        return {"duration": max([video_duration, audio_duration]), "field_order": field_order}

    # TODO: use ffprobe to get width, height instead of the trunc bs
    def start_compress_mkv(
        self,
        overwrite: bool = False,
        deinterlace: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
        single_audio: bool = False,
        crf: int | None = None,
        preset: str = "slow",
        preserve_surround_track: bool = False,
    ):
        """
        Starts ffmpeg with the h264 and AAC codecs for the first video stream and first audio stream.
        Re-containerizes to MP4 and ensures consistency across inputs.
        """
        params_dict = {k: v for k, v in locals().items() if k != "self"}
        if not overwrite and self.output_path.exists():
            raise FileExistsError(f"overwrite=False and {self.output_path} already exists.")

        command = create_ffmpeg_compress_cmd(
            executable=self.executable,
            input_path=self.input_path,
            output_path=self.output_path,
            source_type=self.source_type,
            overwrite=overwrite,
            deinterlace=deinterlace,
            single_audio=single_audio,
            crf=crf,
            preset=preset,
            preserve_surround_track=preserve_surround_track,
        )
        command_str = shlex.join(command)

        if verbose and self.console is not None:
            self.console.print(Text("+ " + command_str))

        if not dry_run:
            self.ffmpeg_proc = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            assert self.ffmpeg_proc.stdout is not None
            assert self.ffmpeg_proc.stderr is not None

            try:
                # log to db
                request_id = create_new_request(
                    "compress", params_dict, command_str, self.ffmpeg_proc.pid
                )
            except Exception as e:
                self.ffmpeg_proc.send_signal(signal.SIGTERM)
                raise e

            interrupted = False
            try:
                yield from self.ffmpeg_proc.stdout
            except KeyboardInterrupt as e:
                interrupted = True
                self.ffmpeg_proc.send_signal(signal.SIGINT)
                raise InterruptedError("FFmpeg Aborted!") from e
            finally:
                res = self.ffmpeg_proc.wait()
                if res != 0 and not interrupted:
                    complete_request(request_id, res, self.ffmpeg_proc.stderr.read(1000))
                    raise RuntimeError(f"ffmpeg failed with exit code {res}")
                else:
                    complete_request(request_id, res)
