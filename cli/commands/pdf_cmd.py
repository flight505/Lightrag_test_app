"""PDF processing commands for LightRAG CLI."""
import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
import json

from ..core.store_manager import StoreManager
from ..core.config import ConfigManager, PDFEngine
from ..core.errors import PDFProcessingError, handle_error
from src.file_processor import FileProcessor
from src.pdf_converter import PDFConverterFactory

console = Console()

@click.group()
@click.pass_context
def pdf(ctx):
    """PDF processing commands."""
    if ctx.obj is None:
        ctx.obj = ConfigManager()

@pdf.command()
@click.argument('file')
@click.argument('store')
@click.option('--engine', type=click.Choice(['auto', 'marker', 'pymupdf', 'pypdf2']), default='marker')
@click.pass_obj
def process(config, file: str, store: str, engine: str):
    """Process a PDF file."""
    try:
        store_manager = StoreManager(config_dir=config.config_dir)
        store_path = store_manager.get_store(store)
        
        processor = FileProcessor(config)
        file_path = Path(file)
        
        if not file_path.exists():
            raise PDFProcessingError(f"PDF file not found: {file}")
            
        with Progress() as progress:
            task = progress.add_task("Processing PDF", total=100)
            
            def update_progress(current, total):
                progress.update(task, completed=int((current/total) * 100))
            
            result = processor.process_file(
                file_path,
                str(store_path),
                engine=PDFEngine[engine.upper()],
                progress_callback=update_progress
            )
            
            if result:
                console.print("✓ Completed successfully", style="green")
                return result
            else:
                raise PDFProcessingError("Processing failed")
                
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@pdf.command()
@click.argument('store')
@click.pass_obj
def list(config, store: str):
    """List processed PDFs in a store."""
    try:
        store_manager = StoreManager(config_dir=config.config_dir)
        store_path = store_manager.get_store(store)
        
        processor = FileProcessor(config)
        pdfs = processor.list_processed_pdfs(str(store_path))
        
        if not pdfs:
            console.print("No PDFs found in store", style="yellow")
            return
            
        table = Table(show_header=True)
        table.add_column("File")
        table.add_column("Title")
        table.add_column("Authors")
        table.add_column("References")
        
        for pdf in pdfs:
            table.add_row(
                pdf['name'],
                pdf['metadata'].get("title", "Unknown"),
                ", ".join(a["name"] for a in pdf['metadata'].get("authors", [])),
                str(len(pdf['metadata'].get("references", [])))
            )
            
        console.print(table)
        
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@pdf.command()
@click.argument('file')
@click.argument('store')
@click.pass_obj
def convert(config, file: str, store: str):
    """Convert PDF to text."""
    try:
        store_manager = StoreManager(config_dir=config.config_dir)
        store_path = store_manager.get_store(store)
        
        processor = FileProcessor(config)
        file_path = Path(file)
        
        if not file_path.exists():
            raise PDFProcessingError(f"PDF file not found: {file}")
            
        with Progress() as progress:
            task = progress.add_task("Converting PDF", total=100)
            
            def update_progress(current, total):
                progress.update(task, completed=int((current/total) * 100))
            
            result = processor.convert_pdf(
                file_path,
                str(store_path),
                progress_callback=update_progress
            )
            
            if result:
                console.print("✓ Conversion complete", style="green")
                return result
            else:
                raise PDFProcessingError("Conversion failed")
                
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@pdf.command()
@click.argument('file')
@click.argument('store')
@click.pass_obj
def info(config, file: str, store: str):
    """Display PDF information."""
    try:
        store_manager = StoreManager(config_dir=config.config_dir)
        store_path = store_manager.get_store(store)
        
        processor = FileProcessor(config)
        file_path = Path(file)
        
        if not file_path.exists():
            raise PDFProcessingError(f"PDF file not found: {file}")
            
        metadata = processor.get_pdf_info(file_path, str(store_path))
        
        if not metadata:
            raise PDFProcessingError("No metadata found")
            
        console.print("\n[bold]PDF Information[/bold]")
        console.print(f"Title: {metadata.get('title', 'Unknown')}")
        console.print(f"Authors: {', '.join(a['name'] for a in metadata.get('authors', []))}")
        console.print(f"References: {len(metadata.get('references', []))}")
        console.print(f"Equations: {len(metadata.get('equations', []))}")
        
    except Exception as e:
        handle_error(e)
        raise click.Abort() 