import re
import signal
import subprocess
from pathlib import Path

from rich.console import Console


class FFmpegClient:
    def __init__(
        self,
        input_path: Path,
        source_type: str = "DVD",
        output_path: Path | None = None,
        overwrite: bool = False,
        executable: str = "ffmpeg",
        console: Console | None = None,
    ):
        self.executable = executable
        self.source_type = source_type
        self.input_path = input_path
        self.overwrite = overwrite
        self.console = console

        if not self.input_path.exists():
            raise FileNotFoundError(f"input_path {input_path} does not exist.")

        if output_path is None:
            self.output_path = (
                self.input_path.parent / f"{self.input_path.stem.replace('_original', '')}.mp4"
            )
        else:
            self.output_path = output_path
        if self.output_path.exists() and not overwrite:
            raise FileExistsError(
                f"output_path {output_path} already exists and overwrite = False."
            )

    def get_ffprobe_duration(self) -> float:
        """Returns the max duration between the first video stream and first audio stream"""
        video_command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream_tags=DURATION-eng",
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
            "^TAG:DURATION-eng=(\\d{2}):(\\d{2}):(\\d{2}.\\d+)$", video_result.stdout.rstrip("\n")
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

        return max([video_duration, audio_duration])

    def start_compress_mkv(self):
        """
        Starts ffmpeg with the h264 and AAC codecs for the first video stream and first audio stream.
        Re-containerizes to MP4 and ensures consistency across inputs.
        """
        command = [self.executable]
        if self.overwrite:
            command.append("-y")
        else:
            command.append("-n")
        command.extend(["-nostdin", "-progress", "pipe:1", "-nostats"])
        command.extend(["-i", str(self.input_path)])
        command.extend(
            ["-map_metadata", "0", "-map_chapters", "0", "-map", "0:v:0", "-map", "0:a:0", "-sn"]
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
        command.extend(
            ["-movflags", "+faststart", "-fflags", "+genpts", "-avoid_negative_ts", "make_zero"]
        )
        if self.source_type == "DVD":
            command.extend(
                ["-vf", "scale=trunc(480*dar/2)*2:480:flags=lanczos,setsar=1,setfield=prog"]
            )
        command.append(str(self.output_path))

        ffmpeg_proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        assert ffmpeg_proc.stdout is not None

        # Hacky fix: use interrupted flag to handle interrupt
        interrupted = False
        try:
            yield from ffmpeg_proc.stdout
        except KeyboardInterrupt:
            ffmpeg_proc.send_signal(signal.SIGINT)
            interrupted = True
        finally:
            res = ffmpeg_proc.wait()
            if interrupted:
                raise InterruptedError("FFmpeg Aborted!")
            if res != 0:
                raise RuntimeError(f"ffmpeg failed with exit code {res}")
