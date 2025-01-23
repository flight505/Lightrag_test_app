"""Metadata management commands for LightRAG CLI."""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import json

from ..core.config import ConfigManager
from ..core.store_manager import StoreManager
from ..core.errors import handle_error, MetadataError, StoreError
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
    """Show metadata for a document"""
    try:
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        if not store_manager.store_exists(store):
            raise MetadataError(f"Store '{store}' not found")
            
        store_path = config.get_store_root() / store
        metadata_file = store_path / "metadata" / f"{Path(document).stem}_metadata.json"
        if not metadata_file.exists():
            raise StoreError(f"No metadata found for document '{document}' in store '{store}'")

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        table = Table(title=f"Metadata for {document}", show_header=True, header_style="bold")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green", overflow="fold", max_width=80)

        field_order = ["title", "authors", "abstract", "references", "equations"]
        for field in field_order:
            value = metadata.get(field)
            if field == "authors":
                value = "No authors found" if not value else ", ".join(a.get("full_name", "Unknown") for a in value)
            elif field == "references":
                value = f"{len(value)} references found" if value else "No references found"
            elif field == "equations":
                value = f"{len(value)} equations found" if value else "No equations found"
            elif field == "abstract":
                value = value[:500] + "..." if value and len(value) > 500 else value
            elif isinstance(value, dict):
                value = json.dumps(value, indent=2)
            elif value is None:
                value = "N/A"
            table.add_row(field, str(value))

        console.print(table)
        return 0
        
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
            return 0
            
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
        consolidator = MetadataConsolidator(store_path=store_path)
        
        with Progress() as progress:
            task = progress.add_task("Consolidating metadata...", total=100)
            consolidator.initialize_consolidated_json()
            progress.update(task, completed=100)
            
        console.print(f"[green]Successfully consolidated metadata for store '{store}'[/green]")
        return 0
        
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
        consolidated_file = store_path / "consolidated.json"
        
        if not consolidated_file.exists():
            raise MetadataError("No consolidated metadata found. Run 'metadata consolidate' first")
            
        with open(consolidated_file, "r", encoding="utf-8") as f:
            consolidated = json.load(f)
            
        # Display statistics in a table
        table = Table(title="Store Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        
        stats = consolidated.get("global_stats", {})
        
        table.add_row("Total Papers", str(stats.get("total_papers", 0)))
        table.add_row("Total Authors", str(stats.get("total_authors", 0)))
        table.add_row("Total Citations", str(stats.get("total_citations", 0)))
        table.add_row("Total Equations", str(stats.get("total_equations", 0)))
        table.add_row("Total Relationships", str(stats.get("total_relationships", 0)))
        
        console.print(table)
        return 0
        
    except Exception as e:
        handle_error(e)
        raise click.Abort() 