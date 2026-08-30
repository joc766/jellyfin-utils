import click

from media_tools.cli.config import AppContext
from media_tools.core.datatypes import ContentType
from media_tools.makemkv_tool.rip_disk import rip_disk


@click.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option("--movie", "content_type", flag_value="movie", default=True)
@click.option("--tv", "content_type", flag_value="tv")
@click.option("--debug", "debug", is_flag=True)
@click.pass_obj
def rip_cmd(
    app_ctx: AppContext, content_type: ContentType, verbose: bool = False, debug: bool = False
):
    try:
        raw_storage_base = app_ctx.config.local_base / "raw" / content_type
        rip_disk(
            raw_storage_base=raw_storage_base, verbose=verbose, debug=debug, console=app_ctx.console
        )
    except InterruptedError as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise e
