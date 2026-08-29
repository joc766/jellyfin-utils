from pathlib import Path

import click
from rich.console import Console

from media_tools.cli.cleanups import find_missing_compressed, find_missing_raw, safe_remove
from media_tools.cli.compress import compress_mkv_cmd
from media_tools.cli.config import AppContext, load_config
from media_tools.cli.organize import organize_cmd
from media_tools.cli.rip import rip_cmd
from media_tools.cli.sync import download, upload

# TODO: make cli interactive vs. fully requiring every parameter
# TODO: utility to see current active users and potentially provide a warning to rsync


@click.group()
@click.pass_context
@click.option("--env-file", "env_file", type=click.Path(path_type=Path))
def cli(ctx: click.Context, env_file: Path | None = None):
    try:
        config = load_config(env_file)
    except (RuntimeError, FileNotFoundError) as e:
        raise click.ClickException(str(e)) from e
    ctx.obj = AppContext(config=config, console=Console())


cli.add_command(organize_cmd, "organize")
cli.add_command(rip_cmd, "rip")
cli.add_command(compress_mkv_cmd, "compress")
cli.add_command(upload)
cli.add_command(download)
cli.add_command(find_missing_raw)
cli.add_command(find_missing_compressed)
cli.add_command(safe_remove)


def main():
    cli()


if __name__ == "__main__":
    main()
