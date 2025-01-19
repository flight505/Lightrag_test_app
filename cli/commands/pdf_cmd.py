"""PDF processing commands for LightRAG CLI."""
import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from ..core.store_manager import StoreManager
from ..core.config import ConfigManager, PDFEngine
from ..core.errors import PDFProcessingError, handle_error
from src.file_processor import FileProcessor

console = Console()

@click.group()
def pdf():
    """PDF document processing commands."""
    pass

@pdf.command()
@click.argument('file')
@click.argument('store')
@click.option('--engine', type=click.Choice(['auto', 'marker', 'pymupdf', 'pypdf2']), default='auto', help="PDF processing engine to use")
def process(file: str, store: str, engine: str):
    """Process a PDF file and add it to a store."""
    try:
        # Initialize managers
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        # Validate store exists
        if not store_manager.store_exists(store):
            raise PDFProcessingError(f"Store '{store}' not found")
            
        # Create file processor with specified engine
        if engine == 'auto':
            # Use PyMuPDF by default for testing
            file_processor = FileProcessor(config, pdf_engine=PDFEngine.PYMUPDF)
        else:
            file_processor = FileProcessor(config, pdf_engine=PDFEngine(engine))
            
        # Set store path
        store_path = store_manager.store_root / store
        file_processor.set_store_path(str(store_path))
        
        # Process file
        with Progress() as progress:
            task = progress.add_task("Processing PDF...", total=100)
            def update_progress(percent):
                progress.update(task, completed=percent)
            result = file_processor.process_file(file, progress_callback=update_progress)
            
        if not result:
            raise PDFProcessingError("Failed to process PDF file")
            
        progress.update(task, completed=100)
        console.print(f"\n✓ Successfully processed {Path(file).name}", style="green")
        
        # Show metadata summary
        metadata = result.get("metadata", {})
        console.print("\nMetadata Summary:", style="bold blue")
        if metadata.get("title"):
            console.print(f"Title: {metadata['title']}")
        if metadata.get("authors"):
            console.print(f"Authors: {', '.join(a['name'] for a in metadata['authors'])}")
        if metadata.get("doi"):
            console.print(f"DOI: {metadata['doi']}")
        if metadata.get("arxiv_id"):
            console.print(f"arXiv ID: {metadata['arxiv_id']}")
        if metadata.get("references"):
            console.print(f"References: {len(metadata['references'])}")
        if metadata.get("equations"):
            console.print(f"Equations: {len(metadata['equations'])}")
            
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@pdf.command()
@click.argument('store')
def list(store: str):
    """List all PDF files in a store."""
    try:
        # Initialize managers
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        # Get store info
        info = store_manager.get_store_info(store)
        
        if not info.get("documents", []):
            console.print("No documents found in store", style="yellow")
            return
            
        # Display documents table
        table = Table(show_header=True)
        table.add_column("File")
        table.add_column("Title")
        table.add_column("Authors")
        table.add_column("DOI/arXiv")
        table.add_column("References")
        
        for doc in info.get("documents", []):
            metadata = doc.get("metadata", {})
            table.add_row(
                doc.get("file", ""),
                metadata.get("title", ""),
                ", ".join(a["name"] for a in metadata.get("authors", [])),
                metadata.get("doi", "") or metadata.get("arxiv_id", ""),
                str(len(metadata.get("references", [])))
            )
            
        console.print(table)
        
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@pdf.command()
@click.argument('store')
@click.argument('file')
def info(store: str, file: str):
    """Show detailed information about a PDF file in a store."""
    try:
        # Initialize managers
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        # Get store info
        info = store_manager.get_store_info(store)
        
        # Find document
        doc = next((d for d in info.get("documents", []) if d["file"] == file), None)
        if not doc:
            raise PDFProcessingError(f"Document '{file}' not found in store '{store}'")
            
        # Display detailed info
        metadata = doc.get("metadata", {})
        console.print(f"\nDocument: {file}", style="bold blue")
        console.print(f"Title: {metadata.get('title', '')}")
        console.print(f"Authors: {', '.join(a['name'] for a in metadata.get('authors', []))}")
        if metadata.get("doi"):
            console.print(f"DOI: {metadata['doi']}")
        if metadata.get("arxiv_id"):
            console.print(f"arXiv ID: {metadata['arxiv_id']}")
        if metadata.get("abstract"):
            console.print(f"\nAbstract:\n{metadata['abstract']}")
        if metadata.get("references"):
            console.print(f"\nReferences: {len(metadata['references'])}")
            for ref in metadata["references"]:
                console.print(f"- {ref.get('title', 'Untitled')}")
        if metadata.get("equations"):
            console.print(f"\nEquations: {len(metadata['equations'])}")
            for eq in metadata["equations"]:
                console.print(f"- {eq.get('latex', '')}")
                
    except Exception as e:
        handle_error(e)
        raise click.Abort() 