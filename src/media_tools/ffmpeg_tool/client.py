import json
import os
import shlex
import signal
import subprocess
from pathlib import Path

from rich.console import Console
from rich.text import Text

from media_tools.db.connection import complete_request, create_new_request
from media_tools.ffmpeg_tool.models import (
    FFProbeAudioStreamInfo,
    FFProbeVideoStreamInfo,
)


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
    preserve_surround_track: bool = False,
):
    command = [executable]
    command.extend(["-v", "error"])
    if overwrite:
        command.append("-y")
    else:
        command.append("-n")
    command.extend(["-nostdin", "-progress", "pipe:1", "-nostats"])

    # INPUT MAPPINGS
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

    # VIDEO CODECS
    if crf is None:
        if source_type == "DVD":
            crf = 20
        else:
            crf = 18

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

    # VIDEO FILTERS
    scale_filter = f"scale=-2:{height}:flags=lanczos" if height is not None else None
    setsar_filter = None
    setfield_filter = "setfield=prog" if deinterlace else None
    deinterlace_filter = "yadif" if deinterlace else None

    if source_type == "DVD":
        setsar_filter = "setsar=1"
        height = 480
        # no reason to go lower than 480p, height parameter does not apply
        scale_filter = f"scale=round({height}*dar/2)*2:{height}:flags=lanczos"

    video_filters = [
        f
        for f in (deinterlace_filter, scale_filter, setsar_filter, setfield_filter)
        if f is not None
    ]

    if len(video_filters) > 0:
        command.extend(["-vf", ",".join(video_filters)])

    # AUDIO CODECS
    command.extend(["-c:a:0", "libfdk_aac", "-ac:a:0", "2", "-ar:a:0", "48000", "-b:a:0", "256k"])
    if not single_audio:
        command.extend(["-c:a:1", "copy" if preserve_surround_track else "libfdk_aac"])
    if not single_audio and not preserve_surround_track:
        command.extend(["-b:a:1", "512k", "-ac:a:1", "6"])

    # AUDIO FILTERS (Stereo)
    command.extend(
        ["-filter:a:0", "acompressor=threshold=-20dB:ratio=3,loudnorm=I=-18:TP=-1.5:LRA=10"]
    )

    # AUDIO METADATA
    if not single_audio:
        command.extend(["-disposition:a:1", "0"])
        command.extend(["-metadata:s:a:1", "title=Surround 5.1"])
    command.extend(["-disposition:a:0", "default"])
    command.extend(["-metadata:s:a:0", "title=Stereo AAC"])

    # MOVFLAGS
    command.extend(["-movflags", "+faststart"])

    # DVD: align timestamps correctly
    if source_type == "DVD":
        command.extend(["-fflags", "+genpts", "-avoid_negative_ts", "make_zero"])
    command.append(str(output_path))

    return command


class FFmpegClient:
    def __init__(
        self,
        *,
        input_path: Path,
        output_path: Path | None = None,
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

    def probe_video(self) -> FFProbeVideoStreamInfo:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_streams",
            "-show_entries",
            "stream=index,codec_name,codec_type,start_pts,start_time,profile,width,height,pix_fmt,level,field_order,sample_aspect_ratio,display_aspect_ratio:stream_disposition=default,original:stream_tags=language,title,DURATION-eng,NUMBER_OF_BYTES-eng,BPS-eng",
            "-of",
            "json",
            str(self.input_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream_info = FFProbeVideoStreamInfo.model_validate(data["streams"][0])
        return stream_info

    def probe_audios(self) -> list[FFProbeAudioStreamInfo]:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:m:language:eng",
            "-show_streams",
            "-show_entries",
            "stream=index,codec_name,codec_type,sample_rate,channels,channel_layout,start_pts,start_time,bit_rate:stream_disposition=default,original",
            "-of",
            "json",
            str(self.input_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)
        all_stream_info = [FFProbeAudioStreamInfo.model_validate(x) for x in data["streams"]]

        return all_stream_info

    def play_audio(self, index: int) -> None:
        play_cmd = ["ffplay", "-ss", "00:05:00", "-vn", "-ast", str(index), str(self.input_path)]
        try:
            subprocess.run(play_cmd, stderr=subprocess.DEVNULL)
        except KeyboardInterrupt:
            pass

    # TODO: use ffprobe to figure out if there's an existing stereo track to encode from
    def start_compress_mkv(
        self,
        overwrite: bool = False,
        deinterlace: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
        single_audio: bool = False,
        height: int | None = None,
        crf: int | None = None,
        preset: str = "slow",
        preserve_surround_track: bool = False,
    ):
        """
        Starts ffmpeg with the h264 and AAC codecs for the first video stream and first audio stream.
        Re-containerizes to MP4 and ensures consistency across inputs.
        """
        params_dict = {k: v for k, v in locals().items() if k != "self"}
        if self.output_path is None:
            raise FileNotFoundError("Output path cannot be None.")
        if not self.output_path.parent.exists():
            raise FileNotFoundError(f"output parent dir {self.output_path.parent} does not exist.")
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
            height=height,
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
                    cli_cmd="compress",
                    cli_params=params_dict,
                    exc_cmd=command_str,
                    pid=self.ffmpeg_proc.pid,
                    parent_pid=os.getpid(),
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
