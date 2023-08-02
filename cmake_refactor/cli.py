import typer
from . import io

cli = typer.Typer()

cli.command()(io.update_links)
