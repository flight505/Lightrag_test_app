from typing import Dict, List, Any, Union, Optional, Callable
from pathlib import Path
from datetime import datetime
import json
import os
from threading import RLock
from src.academic_metadata import MetadataExtractor, AcademicMetadata
from termcolor import colored
from dataclasses import dataclass
from src.pdf_converter import MarkerConverter
import logging

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        self.marker_converter = None  # Will be lazily initialized
        self.metadata_extractor = MetadataExtractor()
        logger.info(f"FileProcessor initialized for store: {store_path}")

    def _ensure_marker_initialized(self):
        """Ensure Marker converter is initialized"""
        if self.marker_converter is None:
            self.marker_converter = MarkerConverter()
            logger.info("Created MarkerConverter instance")

    def _convert_pdf_with_marker(self, pdf_path: str) -> Optional[str]:
        """Convert PDF to text using Marker."""
        try:
            # Initialize marker if needed
            self._ensure_marker_initialized()
            
            # Extract text using MarkerConverter
            text_content = self.marker_converter.extract_text(str(pdf_path))
            
            if not text_content:
                print(colored(f"❌ No text extracted from {Path(pdf_path).name}", "red"))
                return None
            
            return text_content
            
        except Exception as e:
            print(colored(f"❌ Error converting PDF {Path(pdf_path).name}: {str(e)}", "red"))
            return None

    def set_store_path(self, store_path: str) -> None:
        """Set the store path for file processing"""
        self.store_path = store_path
    
    def process_file(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """Process a file and extract its content and metadata"""
        # Initialize result variables
        text: str = ""
        metadata: Dict[str, Any] = {}
        academic_metadata: Dict[str, Any] = {}
        
        try:
            # Validate file
            error = self.config_manager.validate_file(file_path)
            if error:
                print(colored(f"⚠️ File validation failed: {error}", "red"))
                return {"error": error}
            
            # Extract text
            if progress_callback:
                progress_callback("Extracting text...")
            text = self.marker_converter.extract_text(file_path)
            
            # Extract metadata
            if progress_callback:
                progress_callback("Extracting metadata...")
            metadata = self.marker_converter.extract_metadata(file_path)
            
            # Process academic metadata
            if progress_callback:
                progress_callback("Processing academic metadata...")
            academic_metadata = self.metadata_extractor.extract_metadata(
                text=text,
                doc_id=os.path.basename(file_path),
                pdf_path=file_path
            )
            
            # Return combined results
            return {
                "text": text,
                "metadata": metadata,
                "academic_metadata": academic_metadata
            }
            
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            print(colored(f"⚠️ {error_msg}", "red"))
            return {"error": error_msg}
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if the file type is supported"""
        return file_path.lower().endswith('.pdf')