import os
import shlex
import signal
import subprocess
import threading
from collections import deque
from pathlib import Path

from rich.console import Console
from rich.text import Text

from media_tools.db.connection import complete_request, update_pids
from media_tools.ffmpeg_tool.crop_detect import crop_detect
from media_tools.ffmpeg_tool.models import Libx264Tune


def drain_stderr(stderr, log_path: Path, last_lines: deque[str]) -> None:
    with log_path.open("a", encoding="utf-8") as log_file:
        for line in stderr:
            log_file.write(line)
            log_file.flush()
            last_lines.append(line)


def create_ffmpeg_compress_cmd(
    executable: str,
    source_type: str,
    input_path: Path,
    output_path: Path,
    overwrite: bool = False,
    deinterlace: bool = False,
    single_audio: bool = False,
    height: int | None = None,
    crf: int | None = None,
    preset: str = "slow",
    tune: Libx264Tune = None,
    preserve_surround_track: bool = False,
    detect_crop: bool = False,
):
    compress_command = [executable]
    compress_command.extend(["-v", "error"])
    if overwrite:
        compress_command.append("-y")
    else:
        compress_command.append("-n")
    compress_command.extend(["-nostdin", "-progress", "pipe:1", "-nostats"])

    # INPUT MAPPINGS
    compress_command.extend(["-i", str(input_path)])
    compress_command.extend(
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
        compress_command.extend(
            [
                "-map",
                "0:a:0",
            ]
        )

    # VIDEO CODECS
    if crf is None:
        if source_type == "DVD":
            crf = 20
        else:
            crf = 18

    compress_command.extend(
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

    if tune is not None:
        compress_command.extend(["-tune", tune])

    # VIDEO FILTERS
    scale_filter = f"scale=-2:{height}:flags=lanczos" if height is not None else None
    setsar_filter = None
    setfield_filter = "setfield=prog" if deinterlace else None
    deinterlace_filter = "yadif" if deinterlace else None
    crop_filter = crop_detect(input_path) if detect_crop else None

    if source_type == "DVD":
        setsar_filter = "setsar=1"
        # no reason to go lower than 480p, height parameter does not apply
        scale_filter = "scale=round(iw*sar/2)*2:ih:flags=lanczos"

    video_filters = [
        f
        for f in (deinterlace_filter, scale_filter, setsar_filter, setfield_filter, crop_filter)
        if f is not None
    ]

    if len(video_filters) > 0:
        compress_command.extend(["-vf", ",".join(video_filters)])

    # AUDIO CODECS
    compress_command.extend(
        ["-c:a:0", "libfdk_aac", "-ac:a:0", "2", "-ar:a:0", "48000", "-b:a:0", "256k"]
    )
    if not single_audio:
        compress_command.extend(["-c:a:1", "copy" if preserve_surround_track else "libfdk_aac"])
    if not single_audio and not preserve_surround_track:
        compress_command.extend(["-b:a:1", "512k", "-ac:a:1", "6"])

    # AUDIO FILTERS (Stereo)
    compress_command.extend(
        ["-filter:a:0", "acompressor=threshold=-20dB:ratio=3,loudnorm=I=-18:TP=-1.5:LRA=10"]
    )

    # AUDIO METADATA
    if not single_audio:
        compress_command.extend(["-disposition:a:1", "0"])
        compress_command.extend(["-metadata:s:a:1", "title=Surround 5.1"])
    compress_command.extend(["-disposition:a:0", "default"])
    compress_command.extend(["-metadata:s:a:0", "title=Stereo AAC"])

    # MOVFLAGS
    compress_command.extend(["-movflags", "+faststart"])

    # DVD: align timestamps correctly
    if source_type == "DVD":
        compress_command.extend(["-fflags", "+genpts", "-avoid_negative_ts", "make_zero"])
    compress_command.append(str(output_path))

    return compress_command


class FFmpegClient:
    def __init__(
        self,
        *,
        input_path: Path,
        console: Console | None = None,
        source_type: str = "DVD",
        executable: str = "ffmpeg",
    ):
        self.executable = executable
        self.source_type = source_type
        self.input_path = input_path
        self.console = console

        if not self.input_path.exists():
            raise FileNotFoundError(f"input_path {input_path} does not exist.")

    def play_audio(self, index: int) -> None:
        play_cmd = ["ffplay", "-ss", "00:05:00", "-vn", "-ast", str(index), str(self.input_path)]
        try:
            subprocess.run(play_cmd, stderr=subprocess.DEVNULL)
        except KeyboardInterrupt:
            pass

    # TODO: use ffprobe to figure out if there's an existing stereo track to encode from
    def start_compress_mkv(
        self,
        output_path: Path,
        request_id: int | None = None,
        overwrite: bool = False,
        deinterlace: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
        single_audio: bool = False,
        height: int | None = None,
        crf: int | None = None,
        preset: str = "slow",
        tune: Libx264Tune = None,
        preserve_surround_track: bool = False,
        detect_crop: bool = False,
    ):
        """
        Starts ffmpeg with the h264 and AAC codecs for the first video stream and first audio stream.
        Re-containerizes to MP4 and ensures consistency across inputs.
        """
        if not overwrite and output_path.exists():
            raise FileExistsError(f"overwrite=False and {output_path} already exists.")

        compress_command = create_ffmpeg_compress_cmd(
            executable=self.executable,
            input_path=self.input_path,
            output_path=output_path,
            source_type=self.source_type,
            overwrite=overwrite,
            deinterlace=deinterlace,
            single_audio=single_audio,
            height=height,
            crf=crf,
            preset=preset,
            tune=tune,
            preserve_surround_track=preserve_surround_track,
            detect_crop=detect_crop,
        )
        compress_command_str = shlex.join(compress_command)

        if verbose and self.console is not None:
            self.console.print(Text("+ " + compress_command_str))

        if not dry_run:
            ffmpeg_proc = subprocess.Popen(
                compress_command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            assert ffmpeg_proc.stdout is not None
            assert ffmpeg_proc.stderr is not None

            if request_id is not None:
                try:
                    # log to db
                    update_pids(
                        request_id=request_id,
                        exc_cmd=compress_command_str,
                        pid=ffmpeg_proc.pid,
                        parent_pid=os.getpid(),
                    )
                except Exception as e:
                    ffmpeg_proc.send_signal(signal.SIGTERM)
                    raise e

            last_stderr_lines: deque[str] = deque(maxlen=50)
            stderr_thread = threading.Thread(
                target=drain_stderr,
                args=(ffmpeg_proc.stderr, Path("ffmpeg.log"), last_stderr_lines),
                daemon=True,
            )
            stderr_thread.start()

            interrupted = False
            closed = False
            try:
                yield from ffmpeg_proc.stdout

            except KeyboardInterrupt as e:
                ffmpeg_proc.send_signal(signal.SIGINT)
                interrupted = True
                raise InterruptedError("FFmpeg Aborted!") from e

            except GeneratorExit:
                ffmpeg_proc.send_signal(signal.SIGINT)
                closed = True
                raise

            finally:
                try:
                    res = ffmpeg_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    ffmpeg_proc.terminate()
                    res = ffmpeg_proc.wait()

                stderr_thread.join(timeout=5)

                if request_id is not None:
                    if res == 0:
                        complete_request(request_id, "completed", res)
                    elif interrupted or closed:
                        err_excerpt = "".join(last_stderr_lines)
                        complete_request(request_id, "interrupted", res, err_excerpt)
                    else:
                        err_excerpt = "".join(last_stderr_lines)
                        complete_request(request_id, "failed", res, err_excerpt)

                if res != 0 and not interrupted and not closed:
                    raise RuntimeError(f"ffmpeg failed with exit code {res}")
