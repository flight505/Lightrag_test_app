"""Main entry point for LightRAG CLI."""
import click
from rich.console import Console
from rich.traceback import install

from .commands.store_cmd import store
from .core.errors import handle_error

# Install rich traceback handler
install(show_locals=True)

# Initialize rich console
console = Console()

@click.group()
def cli():
    """LightRAG CLI - Academic paper processing and analysis tool."""
    pass

@cli.command()
def version():
    """Show the version of LightRAG."""
    console.print("LightRAG CLI v0.1.0", style="bold green")

# Add command groups
cli.add_command(store)

if __name__ == '__main__':
    try:
        cli()
    except Exception as e:
        handle_error(e)
        raise click.Abort() 