"""Error handling for LightRAG CLI."""
from typing import Type
from rich.console import Console

console = Console()

class LightRAGError(Exception):
    """Base exception for all LightRAG errors."""
    pass

class PDFProcessingError(LightRAGError):
    """PDF processing specific errors."""
    pass

class MetadataError(LightRAGError):
    """Metadata handling errors."""
    pass

class StoreError(LightRAGError):
    """Store management errors."""
    pass

# Error style mapping
ERROR_STYLES = {
    PDFProcessingError: "red bold",
    MetadataError: "yellow bold",
    StoreError: "blue bold",
    LightRAGError: "red"
}

def handle_error(error: Exception) -> None:
    """Handle and display errors with appropriate styling."""
    error_type: Type[Exception] = type(error)
    style = ERROR_STYLES.get(error_type, ERROR_STYLES[LightRAGError])
    console.print(f"Error: {str(error)}", style=style) 