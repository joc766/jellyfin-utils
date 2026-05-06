import subprocess
from pathlib import Path


class FFmpegClient:
    def __init__(
        self,
        input_path: Path,
        source_type: str = "DVD",
        output_path: Path | None = None,
        overwrite: bool = False,
        executable: str = "ffmpeg",
    ):
        self.executable = executable
        self.source_type = source_type
        self.input_path = input_path
        self.overwrite = overwrite

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

    """
        ffmpeg -nostdin -progress pipe:1 -nostats
        -i "/Volumes/SanDisk/raw/tv/HOW_I_MET_YOUR_MOTHER_S2_D1_US/How I Met Your Mother S2E01_original.mkv"
        -map_metadata 0 -map_chapters 0 -map 0:v:0 -map 0:a:0 -sn
        -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high -level 4.1
        -maxrate 20M -bufsize 20M -x264-params interlaced=0
        -c:a libfdk_aac -ac 2 -ab 256k
        -movflags +faststart -fflags +genpts -avoid_negative_ts make_zero
        "/Volumes/SanDisk/raw/tv/HOW_I_MET_YOUR_MOTHER_S2_D1_US/How I Met Your Mother S2E01.mp4
    """

    # TODO: handle overwrite later without -y and -nostdin
    def start_compress_mkv(self):
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

        try:
            yield from ffmpeg_proc.stdout
        finally:
            res = ffmpeg_proc.wait()
            print(res)
            if res != 0:
                raise RuntimeError(f"ffmpeg failed with exit code {res}")
