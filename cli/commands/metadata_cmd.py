"""Metadata management commands for LightRAG CLI."""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import json

from ..core.config import ConfigManager
from ..core.store_manager import StoreManager
from ..core.errors import handle_error, MetadataError
from src.metadata_consolidator import MetadataConsolidator
from src.metadata_extractor import MetadataExtractor

console = Console()

@click.group()
def metadata():
    """Metadata management commands."""
    pass

@metadata.command()
@click.argument('store')
@click.argument('document')
def show(store: str, document: str):
    """Show metadata for a specific document."""
    try:
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        if not store_manager.store_exists(store):
            raise MetadataError(f"Store '{store}' not found")
            
        store_path = config.get_store_root() / store
        metadata_path = store_path / "metadata" / f"{Path(document).stem}_metadata.json"
        
        if not metadata_path.exists():
            raise MetadataError(f"No metadata found for document '{document}'")
            
        # Read metadata directly from JSON file
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Display metadata in a table
        table = Table(title=f"Metadata for {document}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        for field, value in metadata.items():
            if isinstance(value, (list, dict)):
                value = str(value)
            table.add_row(field, str(value))
            
        console.print(table)
        
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@metadata.command()
@click.argument('store')
@click.argument('document')
@click.option('--force', is_flag=True, help="Force metadata extraction even if it exists")
def extract(store: str, document: str, force: bool):
    """Extract metadata for a document."""
    try:
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        if not store_manager.store_exists(store):
            raise MetadataError(f"Store '{store}' not found")
            
        store_path = config.get_store_root() / store
        doc_path = store_path / "documents" / document
        
        if not doc_path.exists():
            raise MetadataError(f"Document '{document}' not found in store")
            
        metadata_path = store_path / "metadata" / f"{Path(document).stem}_metadata.json"
        if metadata_path.exists() and not force:
            raise MetadataError(f"Metadata already exists for '{document}'. Use --force to override")
            
        with Progress() as progress:
            task = progress.add_task("Extracting metadata...", total=100)
            
            # Read document content in binary mode
            with open(doc_path, 'rb') as f:
                content = f.read()
            
            progress.update(task, completed=25)
            
            extractor = MetadataExtractor()
            metadata = extractor.extract_metadata(content, doc_id=document)
            
            progress.update(task, completed=75)
            
            # Save metadata
            metadata_path.parent.mkdir(exist_ok=True)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.model_dump(), f, indent=2)
            
            progress.update(task, completed=100)
            
            console.print("[green]Metadata extracted successfully[/green]")
            
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@metadata.command()
@click.argument('store')
def consolidate(store: str):
    """Consolidate metadata for all documents in a store."""
    try:
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        if not store_manager.store_exists(store):
            raise MetadataError(f"Store '{store}' not found")
            
        store_path = config.get_store_root() / store
        consolidator = MetadataConsolidator(store_path)
        
        with Progress() as progress:
            task = progress.add_task("Consolidating metadata...", total=100)
            consolidator.initialize_consolidated_json()
            progress.update(task, completed=100)
            
        console.print(f"[green]Successfully consolidated metadata for store '{store}'[/green]")
        
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@metadata.command()
@click.argument('store')
def stats(store: str):
    """Show metadata statistics for a store."""
    try:
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        if not store_manager.store_exists(store):
            raise MetadataError(f"Store '{store}' not found")
            
        store_path = config.get_store_root() / store
        consolidator = MetadataConsolidator(store_path)
        consolidated = consolidator._load_json("consolidated.json")
        
        if not consolidated:
            raise MetadataError("No consolidated metadata found. Run 'metadata consolidate' first")
            
        # Display statistics in a table
        table = Table(title="Store Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        
        nodes = consolidated.get("nodes", {})
        relationships = consolidated.get("relationships", [])
        
        table.add_row("Total Papers", str(len(nodes.get("papers", []))))
        table.add_row("Total Authors", str(len(nodes.get("authors", []))))
        table.add_row("Total Citations", str(len(nodes.get("citations", []))))
        table.add_row("Total Equations", str(len(nodes.get("equations", []))))
        table.add_row("Total Relationships", str(len(relationships)))
        
        console.print(table)
        
    except Exception as e:
        handle_error(e)
        raise click.Abort() 