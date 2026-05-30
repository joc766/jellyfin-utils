import re
import signal
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text


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

    def start_compress_mkv(
        self,
        overwrite: bool = False,
        deinterlace: bool = False,
        verbose: bool = False,
    ):
        """
        Starts ffmpeg with the h264 and AAC codecs for the first video stream and first audio stream.
        Re-containerizes to MP4 and ensures consistency across inputs.
        """
        if not overwrite and self.output_path.exists():
            raise FileExistsError(f"overwrite=False and {self.output_path} already exists.")

        command = [self.executable]
        if overwrite:
            command.append("-y")
        else:
            command.append("-n")
        command.extend(["-nostdin", "-progress", "pipe:1", "-nostats"])
        command.extend(["-i", str(self.input_path)])
        command.extend(
            [
                "-map_metadata",
                "0",
                "-map_chapters",
                "0",
                "-map",
                "0:v:0",
                "-map",
                "0:a:m:language:eng",
                "-sn",
            ]
        )
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-level",
                "4.1",
            ]
        )
        command.extend(["-maxrate", "20M", "-bufsize", "20M", "-x264-params", "interlaced=0"])
        command.extend(["-c:a", "libfdk_aac", "-ac", "2", "-ab", "256k"])
        command.extend(["-af", "acompressor=threshold=-20dB:ratio=3,loudnorm=I=-16:TP=-1.5:LRA=10"])
        command.extend(
            ["-movflags", "+faststart", "-fflags", "+genpts", "-avoid_negative_ts", "make_zero"]
        )

        deinterlace_filter = "yadif"
        if self.source_type == "DVD":
            scale_filter = "scale=trunc(480*dar/2)*2:480:flags=lanczos,setsar=1,setfield=prog"
            if deinterlace:
                command.extend(["-vf", f"{deinterlace_filter},{scale_filter}"])
            else:
                command.extend(["-vf", scale_filter])
        elif deinterlace:
            command.extend(["-vf", deinterlace_filter])

        command.append(str(self.output_path))

        if verbose and self.console is not None:
            self.console.print(Text(" ".join(command)))

        self.ffmpeg_proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        assert self.ffmpeg_proc.stdout is not None

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
                raise RuntimeError(f"ffmpeg failed with exit code {res}")
