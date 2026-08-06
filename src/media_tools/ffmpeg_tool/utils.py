import json
import subprocess
from pathlib import Path

from media_tools.ffmpeg_tool.models import FFProbeAudioStreamInfo, FFProbeVideoStreamInfo


def probe_video(path: Path) -> FFProbeVideoStreamInfo:
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
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    stream_info = FFProbeVideoStreamInfo.model_validate(data["streams"][0])
    return stream_info


def probe_audios(path: Path) -> list[FFProbeAudioStreamInfo]:
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
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)

    data = json.loads(result.stdout)
    all_stream_info = [FFProbeAudioStreamInfo.model_validate(x) for x in data["streams"]]

    return all_stream_info
