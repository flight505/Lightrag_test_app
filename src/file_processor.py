import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import json
from transformers import AutoProcessor, AutoModelForVision2Seq
from pdfminer.high_level import extract_text

logger = logging.getLogger(__name__)

# Constants for HuggingFace model
DEVICE = "mps"  # Use Metal Performance Shaders for Apple Silicon
MODEL_NAME = "HuggingFaceM4/idefics2-8b"

class FileProcessor:
    """Handles file preprocessing and tracking"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        
        # Initialize model attributes but don't load yet
        self.processor = None
        self.model = None
        self._model_initialized = False

    def _initialize_model(self):
        """Lazy initialization of HuggingFace model"""
        if not self._model_initialized:
            try:
                logger.info("Loading HuggingFace model...")
                self.processor = AutoProcessor.from_pretrained(MODEL_NAME)
                self.model = AutoModelForVision2Seq.from_pretrained(MODEL_NAME).to(DEVICE)
                self._model_initialized = True
                logger.info("HuggingFace model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading HuggingFace model: {e}")
                self.processor = None
                self.model = None
                self._model_initialized = False
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
            
    def process_file(self, file_path: Path) -> Optional[str]:
        """Process file and return text content"""
        try:
            file_hash = self._calculate_hash(file_path)
            file_info = {
                "original_name": file_path.name,
                "processed_date": datetime.now().isoformat(),
                "hash": file_hash,
                "size": file_path.stat().st_size,
                "type": file_path.suffix.lower()
            }
            
            # Check if file already processed
            if str(file_path) in self.metadata["files"]:
                if self.metadata["files"][str(file_path)]["hash"] == file_hash:
                    logger.info(f"File {file_path} already processed, skipping")
                    return None
                    
            # Process based on file type
            if file_path.suffix.lower() == '.pdf':
                text = self._pdf_to_text(file_path)
                output_path = self.store_path / f"{file_path.stem}.txt"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                file_info["converted_path"] = str(output_path)
            elif file_path.suffix.lower() == '.txt':
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                file_info["converted_path"] = str(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return None
                
            # Update metadata
            self.metadata["files"][str(file_path)] = file_info
            self.metadata["last_updated"] = datetime.now().isoformat()
            self._save_metadata()
            
            return text
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None
            
    def _pdf_to_text(self, pdf_path: Path) -> str:
        """Convert PDF to text using pdfminer and HuggingFace model"""
        try:
            # Use pdfminer for text extraction
            logger.info(f"Extracting text from {pdf_path}...")
            text = extract_text(str(pdf_path))
            
            if not text:
                raise ValueError("No text extracted from PDF")
            
            # Only use HuggingFace if model is initialized
            if self._model_initialized:
                logger.info("Processing text with Idefics2...")
                # Add HuggingFace processing here
                
            return text
            
        except Exception as e:
            logger.error(f"Error in PDF processing: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")
            
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
        
    def process_files(self, files: List[Path], progress_callback=None) -> Dict[str, str]:
        """
        Process multiple files with progress tracking
        Returns: Dict[filename: status]
        """
        results = {}
        total = len(files)
        
        for i, file_path in enumerate(files):
            try:
                # Update progress
                if progress_callback:
                    progress = (i + 1) / total
                    status = f"Processing {file_path.name} ({i + 1}/{total})"
                    progress_callback(progress, status)
                
                # Process file
                text = self.process_file(file_path)
                
                # Store result
                if text:
                    results[file_path.name] = "processed"
                else:
                    results[file_path.name] = "skipped"
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                results[file_path.name] = f"error: {str(e)}"
                
        return results 
        
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
        
        # Only initialize model if we find PDFs to process
        new_files_exist = any(
            str(pdf) not in self.metadata["files"] or 
            self.metadata["files"][str(pdf)]["hash"] != self._calculate_hash(pdf)
            for pdf in pdf_files
        )

        if new_files_exist:
            self._initialize_model()

        # Process only new or modified files
        for pdf_path in pdf_files:
            try:
                file_hash = self._calculate_hash(pdf_path)
                
                # Skip if already processed and unchanged
                if str(pdf_path) in self.metadata["files"]:
                    if self.metadata["files"][str(pdf_path)]["hash"] == file_hash:
                        results[pdf_path.name] = "skipped"
                        continue
                
                # Convert new or modified PDF
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