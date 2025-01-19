"""Search commands for LightRAG CLI."""
import os
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from ..core.store_manager import StoreManager
from ..core.config import ConfigManager
from ..core.errors import SearchError, handle_error
from src.lightrag_init import LightRAGManager

console = Console()

@click.group()
def search():
    """Search and query commands."""
    pass

@search.command()
@click.argument('query')
@click.argument('store')
@click.option('--mode', type=click.Choice(['mix', 'hybrid', 'local', 'global']), default='mix',
              help="Search mode to use")
@click.option('--limit', type=int, default=5, help="Maximum number of results to return")
@click.option('--show-graph', is_flag=True, help="Display knowledge graph for results")
def query(query: str, store: str, mode: str, limit: int, show_graph: bool):
    """Search across documents in a store."""
    try:
        # Initialize managers
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        # Validate store exists
        if not store_manager.store_exists(store):
            raise SearchError(f"Store '{store}' not found")
            
        # Initialize LightRAG
        store_path = store_manager.store_root / store
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SearchError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
            
        rag_manager = LightRAGManager(api_key=api_key, input_dir=str(store_path))
        
        # Perform search with progress
        with Progress() as progress:
            task = progress.add_task("Searching...", total=100)
            
            # Load documents (25%)
            progress.update(task, completed=0, description="Loading documents...")
            rag_manager.load_documents()
            progress.update(task, completed=25)
            
            # Execute search (75%)
            progress.update(task, description="Executing search...")
            results = rag_manager.query(query, mode=mode, limit=limit)
            progress.update(task, completed=75)
            
            # Process results (100%)
            progress.update(task, description="Processing results...")
            if not results:
                console.print("No results found", style="yellow")
                return
                
            # Display results table
            table = Table(show_header=True)
            table.add_column("Document")
            table.add_column("Score")
            table.add_column("Context")
            
            for result in results:
                table.add_row(
                    Path(result["document"]).name,
                    f"{result['score']:.2f}",
                    result["context"][:100] + "..."
                )
            
            console.print("\nSearch Results:", style="bold blue")
            console.print(table)
            
            # Show knowledge graph if requested
            if show_graph:
                progress.update(task, description="Generating knowledge graph...")
                graph = rag_manager.get_citation_graph()
                if graph:
                    console.print("\nKnowledge Graph:", style="bold blue")
                    # Display graph using ASCII art or save to file
                    graph_file = "knowledge_graph.html"
                    graph.save_html(graph_file)
                    console.print(f"Knowledge graph saved to {graph_file}", style="green")
                    
            progress.update(task, completed=100)
            
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@search.command()
@click.argument('store')
@click.option('--type', type=click.Choice(['citations', 'equations', 'authors']), default='citations',
              help="Type of graph to generate")
def graph(store: str, type: str):
    """Generate and display a knowledge graph."""
    try:
        # Initialize managers
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        # Validate store exists
        if not store_manager.store_exists(store):
            raise SearchError(f"Store '{store}' not found")
            
        # Initialize LightRAG
        store_path = store_manager.store_root / store
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SearchError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
            
        rag_manager = LightRAGManager(api_key=api_key, input_dir=str(store_path))
        
        with Progress() as progress:
            task = progress.add_task("Generating graph...", total=100)
            
            # Load documents
            progress.update(task, description="Loading documents...")
            rag_manager.load_documents()
            progress.update(task, completed=50)
            
            # Generate graph
            progress.update(task, description="Building graph...")
            if type == 'citations':
                graph = rag_manager.get_citation_graph()
            elif type == 'equations':
                graph = rag_manager.get_equation_graph()
            else:  # authors
                graph = rag_manager.get_author_graph()
                
            if not graph:
                console.print(f"No {type} found to generate graph", style="yellow")
                return
                
            # Save graph
            graph_file = f"{type}_graph.html"
            graph.save_html(graph_file)
            progress.update(task, completed=100)
            
            console.print(f"\n✓ {type.title()} graph saved to {graph_file}", style="green")
            
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@search.command()
@click.argument('store')
def stats(store: str):
    """Show search statistics for a store."""
    try:
        # Initialize managers
        config = ConfigManager()
        store_manager = StoreManager(config_dir=config.config_dir)
        
        # Validate store exists
        if not store_manager.store_exists(store):
            raise SearchError(f"Store '{store}' not found")
            
        # Initialize LightRAG
        store_path = store_manager.store_root / store
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SearchError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
            
        rag_manager = LightRAGManager(api_key=api_key, input_dir=str(store_path))
        
        # Get stats
        stats = rag_manager.get_stats()
        
        # Display stats
        console.print("\nStore Statistics:", style="bold blue")
        console.print(f"Total Documents: {stats['total_documents']}")
        console.print(f"Total Citations: {stats['total_citations']}")
        console.print(f"Total Equations: {stats['total_equations']}")
        console.print(f"Total Authors: {stats['total_authors']}")
        console.print(f"Total Relationships: {stats['total_relationships']}")
        
        if stats.get('embedding_stats'):
            console.print("\nEmbedding Statistics:", style="bold blue")
            for key, value in stats['embedding_stats'].items():
                console.print(f"{key}: {value}")
                
    except Exception as e:
        handle_error(e)
        raise click.Abort() 