import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)

# Configuration for Marker PDF conversion
MARKER_CONFIG = {
    "output_format": "markdown",
    "force_ocr": True,
    "num_workers": 8
}

class FileProcessor:
    """Handles file preprocessing and tracking"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        self.pdf_converter = None  # Initialize converter only when needed
        logger.info(f"FileProcessor initialized for store: {store_path}")

    def _initialize_marker(self):
        """Lazy initialization of Marker converter"""
        if self.pdf_converter is None:
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict
                from marker.config.parser import ConfigParser
                
                logger.info("Initializing Marker PDF converter...")
                self.config_parser = ConfigParser(MARKER_CONFIG)
                self.pdf_converter = PdfConverter(
                    config=self.config_parser.generate_config_dict(),
                    artifact_dict=create_model_dict(),
                )
                logger.info("Marker PDF converter initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Marker: {e}")
                raise

    def _pdf_to_text(self, pdf_path: Path) -> str:
        """Convert PDF to text using Marker"""
        try:
            # Initialize Marker only when needed
            if self.pdf_converter is None:
                self._initialize_marker()
            
            logger.info(f"Converting {pdf_path} to text using Marker...")
            rendered = self.pdf_converter(str(pdf_path))
            text = rendered.markdown
            
            if not text:
                raise ValueError("No text extracted from PDF")
                
            logger.info(f"Successfully converted {pdf_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error in PDF processing: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def _load_metadata(self) -> Dict:
        """Load or create metadata file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "files": {},
            "last_updated": datetime.now().isoformat()
        }
        
    def _save_metadata(self):
        """Save metadata to file"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=4)
            
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash for tracking changes"""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def scan_and_convert_store(self) -> Dict[str, str]:
        """
        Scan store directory for new PDFs and convert them to text
        Returns: Dict[filename: status]
        """
        results = {}
        pdf_files = list(self.store_path.glob("*.pdf"))
        
        if not pdf_files:
            logger.info(f"No PDF files found in {self.store_path}")
            return results
        
        logger.info(f"Found {len(pdf_files)} PDF files to check")
        
        # Check for new or modified PDFs before initializing Marker
        new_files_exist = any(
            str(pdf) not in self.metadata["files"] or 
            self.metadata["files"][str(pdf)]["hash"] != self._calculate_hash(pdf)
            for pdf in pdf_files
        )
        
        if not new_files_exist:
            logger.info("No new or modified PDFs found")
            return {pdf.name: "skipped" for pdf in pdf_files}
        
        # Process each PDF file
        for pdf_path in pdf_files:
            try:
                file_hash = self._calculate_hash(pdf_path)
                
                # Skip if already processed and unchanged
                if str(pdf_path) in self.metadata["files"]:
                    if self.metadata["files"][str(pdf_path)]["hash"] == file_hash:
                        results[pdf_path.name] = "skipped"
                        continue
                
                # Convert PDF to text using Marker
                text = self._pdf_to_text(pdf_path)
                if not text:
                    results[pdf_path.name] = "failed: no text extracted"
                    continue
                
                # Save text file
                text_path = self.store_path / f"{pdf_path.stem}.txt"
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text)
                
                # Update metadata
                self.metadata["files"][str(pdf_path)] = {
                    "original_name": pdf_path.name,
                    "processed_date": datetime.now().isoformat(),
                    "hash": file_hash,
                    "size": pdf_path.stat().st_size,
                    "type": ".pdf",
                    "converted_path": str(text_path)
                }
                self._save_metadata()
                
                results[pdf_path.name] = "converted"
                logger.info(f"Successfully converted {pdf_path.name}")
                
            except Exception as e:
                logger.error(f"Error converting {pdf_path.name}: {str(e)}")
                results[pdf_path.name] = f"error: {str(e)}"
        
        return results

    def cleanup_unused(self) -> List[str]:
        """Remove files that are no longer needed"""
        removed = []
        for file_path in list(self.metadata["files"].keys()):
            if not Path(file_path).exists():
                info = self.metadata["files"][file_path]
                if "converted_path" in info:
                    conv_path = Path(info["converted_path"])
                    if conv_path.exists():
                        conv_path.unlink()
                del self.metadata["files"][file_path]
                removed.append(file_path)
        
        self._save_metadata()
        return removed