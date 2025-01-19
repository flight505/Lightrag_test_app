"""Store management commands for LightRAG CLI."""
import click
from rich.console import Console
from rich.table import Table
from pathlib import Path

from ..core.store_manager import StoreManager
from ..core.config import ConfigManager
from ..core.errors import StoreError, handle_error

console = Console()

@click.group()
def store():
    """Manage document stores."""
    pass

@store.command()
@click.argument('name')
def create(name: str):
    """Create a new document store."""
    try:
        config = ConfigManager()
        manager = StoreManager(config_dir=config.config_dir)
        manager.create_store(name)
        return 0
    except StoreError as e:
        handle_error(e)
        raise click.Abort()
    except Exception as e:
        handle_error(StoreError(f"Failed to create store: {str(e)}"))
        raise click.Abort()

@store.command()
@click.argument('name')
@click.option('--force', is_flag=True, help="Skip confirmation prompt")
def delete(name: str, force: bool = False):
    """Delete a document store."""
    try:
        config = ConfigManager()
        manager = StoreManager(config_dir=config.config_dir)
        if not force and not click.confirm(f"Are you sure you want to delete store '{name}'?"):
            return
        manager.delete_store(name)
        return 0
    except StoreError as e:
        handle_error(e)
        raise click.Abort()
    except Exception as e:
        handle_error(StoreError(str(e)))
        raise click.Abort()

@store.command()
def list():
    """List all document stores."""
    try:
        config = ConfigManager()
        manager = StoreManager(config_dir=config.config_dir)
        stores = manager.list_stores()
        
        if not stores:
            console.print("No stores found", style="yellow")
            return 0
            
        table = Table(show_header=True)
        table.add_column("Name")
        table.add_column("Documents")
        table.add_column("Size")
        table.add_column("Created")
        table.add_column("Updated")
        
        for store_name in stores:
            info = manager.get_store_info(store_name)
            table.add_row(
                store_name,
                str(info["document_count"]),
                f"{info['size'] / 1024 / 1024:.1f} MB",
                info["created"].split("T")[0],
                info["updated"].split("T")[0]
            )
            
        console.print(table)
        return 0
    except StoreError as e:
        handle_error(e)
        raise click.Abort()
    except Exception as e:
        handle_error(StoreError(str(e)))
        raise click.Abort()

@store.command()
@click.argument('name')
def info(name: str):
    """Show detailed information about a store."""
    try:
        config = ConfigManager()
        manager = StoreManager(config_dir=config.config_dir)
        info = manager.get_store_info(name)
        
        console.print(f"\nStore: {name}", style="bold blue")
        console.print(f"Path: {info['path']}")
        console.print(f"Documents: {info['document_count']}")
        console.print(f"Size: {info['size'] / 1024 / 1024:.1f} MB")
        console.print(f"Created: {info['created']}")
        console.print(f"Updated: {info['updated']}\n")
        return 0
    except StoreError as e:
        handle_error(e)
        raise click.Abort()
    except Exception as e:
        handle_error(StoreError(str(e)))
        raise click.Abort() 