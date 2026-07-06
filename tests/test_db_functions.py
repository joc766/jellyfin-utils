import shlex

from media_tools.db.connection import complete_request, create_new_request, init_db
from media_tools.ffmpeg_tool.client import create_ffmpeg_compress_cmd


def test_init_db(tmp_path):
    db_path = tmp_path / "db.sqlite"
    init_db(db_path)
    params = {
        "disc_type": "BD",
        "content_type": "movie",
        "overwrite": False,
        "verbose": False,
        "single_audio": False,
        "preserve_surround": True,
        "crf": "18",
        "preset": "slow",
        "dry_run": False,
    }
    # shell_cmd = create_ffmpeg_compress_cmd(
    #     executable="ffmpeg",
    #     source_type=params["disc_type"],
    #     input_path=tmp_path / "test.mp4",
    #     output_path=tmp_path / "test-out.mp4",
    #     overwrite=params["overwrite"],
    #     deinterlace=False,
    #     single_audio=False,
    #     crf=params["crf"],
    #     preset=params["preset"],
    #     preserve_surround_track=params["preserve_surround"],
    # )
    # shell_cmd_str = shlex.join(shell_cmd)
    # pid = 9999
    # parent_pid = 9998
    request_id = create_new_request(
        cli_cmd="compress",
        cli_params=params,
        db_path=db_path,
    )
    complete_request(request_id, "test_complete", 0, db_path=db_path)
