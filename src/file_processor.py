import os
import logging
from typing import Dict, List, Any, Union, Optional, Callable
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
from threading import RLock
from src.academic_metadata import MetadataExtractor, AcademicMetadata
from termcolor import colored
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChunkingConfig:
    """Configuration for text chunking"""
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 1000
    
    def validate(self) -> None:
        """Validate chunking configuration"""
        if self.chunk_size < self.min_chunk_size:
            raise ValueError(f"Chunk size must be at least {self.min_chunk_size}")
        if self.chunk_size > self.max_chunk_size:
            raise ValueError(f"Chunk size must be at most {self.max_chunk_size}")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if self.chunk_overlap < 0:
            raise ValueError("Chunk overlap must be non-negative")

@dataclass
class BatchInserter:
    """Handles batch insertion of documents with progress tracking"""
    batch_size: int = 10
    max_retries: int = 3
    timeout: int = 60
    
    def __init__(self):
        self.lock = RLock()
        self.current_batch = []
        self.failed_items = []
    
    def add_item(self, item: Any) -> None:
        """Add item to current batch"""
        with self.lock:
            self.current_batch.append(item)
            if len(self.current_batch) >= self.batch_size:
                self.flush()
    
    def flush(self) -> None:
        """Process and clear current batch"""
        with self.lock:
            if not self.current_batch:
                return
            
            try:
                # Process batch
                for item in self.current_batch:
                    try:
                        self._process_item(item)
                    except Exception as e:
                        print(colored(f"⚠️ Failed to process item: {e}", "yellow"))
                        self.failed_items.append((item, str(e)))
                
                self.current_batch.clear()
                
            except Exception as e:
                print(colored(f"❌ Batch processing error: {e}", "red"))
                self.failed_items.extend((item, "Batch error") for item in self.current_batch)
                self.current_batch.clear()
    
    def _process_item(self, item: Any) -> None:
        """Process individual item with retries"""
        for attempt in range(self.max_retries):
            try:
                # Implement actual processing logic here
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                print(colored(f"⚠️ Retry {attempt + 1}/{self.max_retries}: {e}", "yellow"))
    
    def get_failed_items(self) -> List[tuple]:
        """Get list of failed items and their error messages"""
        return self.failed_items.copy()
    
    def clear_failed_items(self) -> None:
        """Clear the list of failed items"""
        self.failed_items.clear()

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        self.pdf_converter = None
        self.metadata_extractor = MetadataExtractor()
        logger.info(f"FileProcessor initialized for store: {store_path}")

    def _initialize_marker(self):
        """Initialize Marker converter with configuration"""
        try:
            # Disable tokenizers warning
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.config.parser import ConfigParser
            
            # Configure marker with optimizations for M3 Max
            config = {
                "output_format": "markdown",
                "force_ocr": False,  # Only use OCR when needed
                "extract_images": False,  # Skip image extraction for speed
                "batch_multiplier": 12,  # Larger batches for M3 Max
                "num_workers": 8,  # Parallel workers
                "langs": ["English"],  # Optimize for English
                "device": "mps",  # Use Metal Performance Shaders
                "model_precision": "float16",  # Use half precision
                "max_batch_size": 16,  # Larger batch size
                
                # Layout detection settings
                "layout_coverage_min_lines": 2,
                "layout_coverage_threshold": 0.4,
                "document_ocr_threshold": 0.7,
                "error_model_segment_length": 1024,
                
                # OCR settings
                "detection_batch_size": 8,
                "recognition_batch_size": 8,
                
                # LLM settings
                "use_llm": True,
                "google_api_key": os.getenv("GEMINI_API_KEY"),
                "model_name": "gemini-1.5-flash",
                "max_retries": 3,
                "max_concurrency": 3,
                "timeout": 60,
                "confidence_threshold": 0.75,
            }
            
            # Initialize the converter with default processor list
            self.pdf_converter = PdfConverter(
                artifact_dict=create_model_dict(),
                config=config,
                renderer="marker.renderers.markdown.MarkdownRenderer"
            )
            
            # Enable LLM if configured
            if config["use_llm"]:
                self.pdf_converter.use_llm = True
            
            logger.info("Initialized Marker PDF converter with M3 Max optimized configuration")
            logger.info(f"Using configuration: {config}")
            
            print(colored("✓ Initialized Marker PDF converter", "green"))
            
        except ImportError as e:
            error_msg = f"Failed to initialize Marker: {e}"
            logger.error(error_msg)
            print(colored(f"❌ {error_msg}", "red"))
            raise

    def process_pdf_with_marker(self, file_path: Union[str, List[str]], cleanup_pdfs: bool = True, progress_callback: Optional[Callable] = None) -> bool:
        """Process PDF file(s) with Marker."""
        try:
            # Handle single file or list of files
            if isinstance(file_path, str):
                files_to_process = [file_path]
            else:
                files_to_process = file_path
            
            results = []
            for pdf_path in files_to_process:
                try:
                    # Convert PDF to text
                    txt_path = Path(pdf_path).with_suffix('.txt')
                    if progress_callback:
                        progress_callback(f"Converting {Path(pdf_path).name}...")
                    
                    text = self._convert_pdf_with_marker(pdf_path)
                    if not text:
                        continue
                    
                    # Save text content
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    # Extract academic metadata
                    if progress_callback:
                        progress_callback(f"Extracting metadata from {Path(pdf_path).name}...")
                    
                    metadata = self.metadata_extractor.extract_metadata(
                        text=text,
                        doc_id=Path(pdf_path).stem
                    )
                    
                    # Save metadata
                    metadata.save(Path(pdf_path).parent)
                    
                    # Update metadata store
                    self.metadata["files"][Path(pdf_path).name] = {
                        "path": str(pdf_path),
                        "txt_path": str(txt_path),
                        "academic_metadata": metadata.to_dict()
                    }
                    self._save_metadata()
                    
                    # Cleanup PDF if requested
                    if cleanup_pdfs:
                        try:
                            Path(pdf_path).unlink()
                            print(colored(f"✓ Removed PDF after successful conversion: {Path(pdf_path).name}", "green"))
                        except Exception as e:
                            print(colored(f"⚠️ Failed to remove PDF {Path(pdf_path).name}: {e}", "yellow"))
                    
                    results.append(True)
                    print(colored(f"✓ Successfully processed {Path(pdf_path).name}", "green"))
                    
                except Exception as e:
                    print(colored(f"❌ Error processing {pdf_path}: {str(e)}", "red"))
                    results.append(False)
            
            return any(results)
            
        except Exception as e:
            print(colored(f"❌ Error in process_pdf_with_marker: {str(e)}", "red"))
            return False

    def _load_metadata(self) -> Dict:
        """Load metadata from file or create new if not exists"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"files": {}, "last_updated": None}
        
    def _save_metadata(self) -> None:
        """Save metadata to file"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

    def clean_unused_files(self) -> Dict[str, List[str]]:
        """Clean unused files from the store directory"""
        try:
            all_files = list(self.store_path.glob("*.*"))
            used_files = set()
            removed_files = {"txt": [], "json": [], "other": []}
            
            # Find used files from metadata
            if self.metadata_file.exists():
                for doc_info in self.metadata["files"].values():
                    if isinstance(doc_info, dict):
                        if "source" in doc_info:
                            txt_file = self.store_path / doc_info["source"]
                            used_files.add(txt_file)
                            # Keep both metadata files
                            json_file = txt_file.with_suffix('.json')
                            academic_json = self.store_path / f"{txt_file.stem}_metadata.json"
                            if json_file.exists():
                                used_files.add(json_file)
                            if academic_json.exists():
                                used_files.add(academic_json)
                        if "original_source" in doc_info:
                            used_files.add(self.store_path / doc_info["original_source"])
            
            # Remove unused files
            for file_path in all_files:
                if file_path not in used_files and file_path != self.metadata_file:
                    try:
                        suffix = file_path.suffix.lower()
                        category = suffix[1:] if suffix in ['.txt', '.json'] else 'other'
                        removed_files[category].append(str(file_path))
                        file_path.unlink()
                        print(colored(f"✓ Removed unused file: {file_path.name}", "green"))
                    except Exception as e:
                        print(colored(f"❌ Error removing file {file_path.name}: {str(e)}", "red"))
            
            return removed_files
            
        except Exception as e:
            error_msg = f"Error cleaning unused files: {str(e)}"
            logger.error(error_msg)
            print(colored(f"❌ {error_msg}", "red"))
            raise

    def get_citation_network(self) -> Dict[str, List[str]]:
        """Build citation network from document references"""
        network = {}
        for doc_name, doc_info in self.metadata["files"].items():
            if "academic_metadata" in doc_info:
                academic_metadata = AcademicMetadata.from_dict(doc_info["academic_metadata"])
                citations = []
                for ref in academic_metadata.references:
                    if ref.citation_key:
                        citations.append(ref.citation_key)
                network[doc_name] = citations
        return network

    def analyze_equations(self) -> Dict[str, Any]:
        """Analyze equations across all documents"""
        stats = {
            "total_equations": 0,
            "documents_with_equations": 0,
            "equation_types": {
                "differential": 0,
                "matrix": 0,
                "statistical": 0,
                "algebraic": 0
            }
        }
        
        for doc_info in self.metadata["files"].values():
            if "academic_metadata" in doc_info:
                academic_metadata = AcademicMetadata.from_dict(doc_info["academic_metadata"])
                if academic_metadata.equations:
                    stats["documents_with_equations"] += 1
                    stats["total_equations"] += len(academic_metadata.equations)
                    
                    for equation in academic_metadata.equations:
                        if equation.equation_type:
                            stats["equation_types"][equation.equation_type] += 1
        
        return stats

    def _convert_pdf_with_marker(self, pdf_path: str) -> Optional[str]:
        """Convert PDF to text using Marker."""
        try:
            # Initialize marker if needed
            if self.pdf_converter is None:
                self._initialize_marker()
            
            # Convert using marker's Python API
            rendered = self.pdf_converter(str(pdf_path))
            text_content = rendered.markdown
            
            if not text_content:
                print(colored(f"❌ No text extracted from {Path(pdf_path).name}", "red"))
                return None
            
            return text_content
            
        except Exception as e:
            print(colored(f"❌ Error converting PDF {Path(pdf_path).name}: {str(e)}", "red"))
            return None