import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re

logger = logging.getLogger(__name__)

# Configuration for Marker PDF conversion with equation focus
MARKER_CONFIG = {
    "output_format": "markdown",
    "force_ocr": True,
    "num_workers": 8,
    "equation_mode": True  # Enable special handling for equations
}

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        self.pdf_converter = None
        self.equation_pattern = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
        logger.info(f"FileProcessor initialized for store: {store_path}")

    def _extract_equations(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract LaTeX equations and generate unique identifiers
        Returns: List of (equation_id, equation_latex) tuples
        """
        equations = []
        for idx, match in enumerate(self.equation_pattern.finditer(text)):
            equation = match.group(1).strip()
            equation_id = f"eq_{hashlib.md5(equation.encode()).hexdigest()[:8]}"
            equations.append((equation_id, equation))
        return equations

    def _process_text_with_equations(self, text: str) -> Tuple[str, Dict]:
        """
        Process text and extract equation metadata
        Returns: (processed_text, equation_metadata)
        """
        equations = self._extract_equations(text)
        equation_metadata = {
            "equations": [
                {
                    "id": eq_id,
                    "latex": eq_latex,
                    "position": idx
                }
                for idx, (eq_id, eq_latex) in enumerate(equations)
            ]
        }
        return text, equation_metadata

    def _pdf_to_text(self, pdf_path: Path) -> Tuple[str, Dict]:
        """Convert PDF to text using Marker with equation handling"""
        try:
            if self.pdf_converter is None:
                self._initialize_marker()
            
            logger.info(f"Converting {pdf_path} to text with equation extraction...")
            rendered = self.pdf_converter(str(pdf_path))
            text = rendered.markdown
            
            if not text:
                raise ValueError("No text extracted from PDF")
            
            # Process text and extract equations
            processed_text, equation_metadata = self._process_text_with_equations(text)
            
            logger.info(f"Successfully converted {pdf_path} with {len(equation_metadata['equations'])} equations")
            return processed_text, equation_metadata
            
        except Exception as e:
            logger.error(f"Error in PDF processing: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

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
        """Scan store directory for new PDFs and convert them to text"""
        results = {}
        pdf_files = list(self.store_path.glob("*.pdf"))
        
        if not pdf_files:
            logger.info(f"No PDF files found in {self.store_path}")
            return results
        
        # Check for new/modified files before initializing Marker
        new_files_exist = any(
            str(pdf) not in self.metadata["files"] or 
            self.metadata["files"][str(pdf)]["hash"] != self._calculate_hash(pdf)
            for pdf in pdf_files
        )
        
        if not new_files_exist:
            logger.info("No new or modified PDFs found")
            return {pdf.name: "skipped" for pdf in pdf_files}
        
        for pdf_path in pdf_files:
            try:
                file_hash = self._calculate_hash(pdf_path)
                
                if str(pdf_path) in self.metadata["files"]:
                    if self.metadata["files"][str(pdf_path)]["hash"] == file_hash:
                        results[pdf_path.name] = "skipped"
                        continue
                
                # Convert and extract equations
                text, equation_metadata = self._pdf_to_text(pdf_path)
                
                # Save text content
                text_path = self.store_path / f"{pdf_path.stem}.txt"
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text)
                
                # Save equation metadata separately
                equation_path = self.store_path / f"{pdf_path.stem}_equations.json"
                with open(equation_path, "w", encoding="utf-8") as f:
                    json.dump(equation_metadata, f, indent=2)
                
                # Update metadata with equation information
                self.metadata["files"][str(pdf_path)] = {
                    "original_name": pdf_path.name,
                    "processed_date": datetime.now().isoformat(),
                    "hash": file_hash,
                    "size": pdf_path.stat().st_size,
                    "type": ".pdf",
                    "converted_path": str(text_path),
                    "equation_metadata_path": str(equation_path),
                    "equation_count": len(equation_metadata["equations"])
                }
                self._save_metadata()
                
                results[pdf_path.name] = f"converted (with {len(equation_metadata['equations'])} equations)"
                logger.info(f"Successfully processed {pdf_path.name}")
                
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