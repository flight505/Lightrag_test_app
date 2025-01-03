import os
import logging
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
import streamlit as st
from stqdm import stqdm
from threading import RLock

# Set lock for stqdm to prevent issues
stqdm.set_lock(RLock())

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.metadata_file = self.store_path / "metadata.json"
        self.metadata = self._load_metadata()
        self.pdf_converter = None
        self.equation_pattern = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
        self.reference_pattern = re.compile(r'\[@(.*?)\]', re.DOTALL)
        logger.info(f"FileProcessor initialized for store: {store_path}")

    def _extract_equations(self, text: str) -> List[tuple[str, str]]:
        """Extract LaTeX equations and generate unique identifiers"""
        equations = []
        for idx, match in enumerate(self.equation_pattern.finditer(text)):
            equation = match.group(1).strip()
            equation_id = f"eq_{hashlib.md5(equation.encode()).hexdigest()[:8]}"
            equations.append((equation_id, equation))
        return equations

    def _extract_references(self, text: str) -> List[str]:
        """Extract academic references from the text"""
        return [ref.group(1) for ref in self.reference_pattern.finditer(text)]

    def _initialize_marker(self):
        """Initialize Marker converter with configuration"""
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.config.parser import ConfigParser
            
            # Configure marker with optimizations for M3 Max
            config = {
                "output_format": "markdown",
                "force_ocr": True,  # Ensure consistent text extraction
                "extract_images": False,  # Skip image extraction for speed
                "batch_multiplier": 12,  # Larger batches for M3 Max (40 cores)
                "num_workers": 8,  # Parallel workers for processing
                "langs": ["English"],  # Optimize for English only
                "device": "mps",  # Use Metal Performance Shaders
                "model_precision": "float16",  # Use half precision for better performance
                "max_batch_size": 16,  # Larger batch size for faster processing
                "debug": False,  # Disable debug output for speed
            }
            
            config_parser = ConfigParser(config)
            
            self.pdf_converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer()
            )
            logger.info("Initialized Marker PDF converter with M3 Max optimized configuration")
            logger.info(f"Using configuration: {config}")
        except ImportError as e:
            logger.error(f"Failed to initialize Marker: {e}")
            raise

    def process_pdf_with_marker(self, file_paths: List[str], progress_callback=None, cleanup_pdfs: bool = True) -> List[Dict[str, Any]]:
        """Process PDFs using Marker's Python API"""
        try:
            if isinstance(file_paths, str):
                file_paths = [file_paths]
            
            results = []
            total_files = len(file_paths)
            
            # Initialize marker if needed
            if self.pdf_converter is None:
                with st.spinner("Initializing Marker..."):
                    self._initialize_marker()
            
            # Process each file with progress bar
            for idx, file_path in enumerate(stqdm(
                file_paths, 
                desc="Converting documents",
                total=total_files,
                unit="file",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            ), 1):
                base_name = Path(file_path).stem
                
                try:
                    if progress_callback:
                        progress_callback(f"Processing {base_name} ({idx}/{total_files})")
                    
                    # Progress placeholder for file info
                    info_ph = st.empty()
                    info_ph.info(f"Converting {base_name}...")
                    
                    # Convert using marker's Python API
                    rendered = self.pdf_converter(str(file_path))
                    text_content = rendered.markdown
                    
                    if not text_content:
                        info_ph.error(f"❌ No text extracted from {base_name}")
                        continue
                    
                    # Save the text content
                    txt_path = self.store_path / f"{base_name}.txt"
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    
                    # Create metadata
                    metadata = {
                        "table_of_contents": rendered.toc if hasattr(rendered, 'toc') else [],
                        "page_stats": rendered.page_stats if hasattr(rendered, 'page_stats') else [],
                        "equations": self._extract_equations(text_content),
                        "references": self._extract_references(text_content)
                    }
                    
                    # Save metadata
                    json_path = self.store_path / f"{base_name}.json"
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2)
                    
                    # Update metadata in memory
                    self.metadata["files"][base_name] = {
                        "source": os.path.basename(txt_path),
                        "original_source": os.path.basename(file_path),
                        "created": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                        "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                        "file_type": "txt",
                        "original_type": "pdf",
                        "marker_metadata": {
                            "toc": metadata["table_of_contents"],
                            "page_stats": metadata["page_stats"]
                        },
                        "equations": metadata["equations"],
                        "references": metadata["references"]
                    }
                    
                    results.append({
                        "content": text_content,
                        "metadata": self.metadata["files"][base_name]
                    })
                    
                    # Cleanup PDF if requested
                    if cleanup_pdfs:
                        try:
                            Path(file_path).unlink()
                            info_ph.success(f"✅ Completed processing {base_name} and removed PDF")
                            logger.info(f"Removed PDF after successful conversion: {file_path}")
                        except Exception as e:
                            info_ph.warning(f"✅ Completed processing {base_name} but failed to remove PDF: {e}")
                            logger.warning(f"Failed to remove PDF {file_path}: {e}")
                    else:
                        info_ph.success(f"✅ Completed processing {base_name}")
                
                except Exception as e:
                    error_msg = f"Error processing {base_name}: {str(e)}"
                    if progress_callback:
                        progress_callback(f"❌ {error_msg}")
                    logger.error(error_msg)
                    st.error(error_msg)
                    continue
            
            # Save all metadata at once
            self._save_metadata()
            return results
            
        except Exception as e:
            error_msg = f"Error in processing: {str(e)}"
            if progress_callback:
                progress_callback(f"❌ {error_msg}")
            logger.error(error_msg)
            st.error(error_msg)
            raise

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
                            json_file = txt_file.with_suffix('.json')
                            if json_file.exists():
                                used_files.add(json_file)
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
                        logger.info(f"Removed unused file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {str(e)}")
            
            return removed_files
            
        except Exception as e:
            logger.error(f"Error cleaning unused files: {str(e)}")
            raise

    def search_equations(self, query: str) -> List[Dict[str, Any]]:
        """Search for equations across all documents using pattern matching"""
        results = []
        for doc_name, doc_info in self.metadata["files"].items():
            if "equations" in doc_info:
                for eq_id, equation in doc_info["equations"]:
                    if query.lower() in equation.lower():
                        results.append({
                            "document": doc_name,
                            "equation_id": eq_id,
                            "equation": equation,
                            "source": doc_info.get("original_source", "")
                        })
        return results

    def get_equation_by_id(self, equation_id: str) -> Dict[str, Any]:
        """Retrieve specific equation by its ID"""
        for doc_name, doc_info in self.metadata["files"].items():
            if "equations" in doc_info:
                for eq_id, equation in doc_info["equations"]:
                    if eq_id == equation_id:
                        return {
                            "document": doc_name,
                            "equation": equation,
                            "source": doc_info.get("original_source", ""),
                            "context": self._get_equation_context(doc_name, equation)
                        }
        return None

    def get_citation_network(self) -> Dict[str, List[str]]:
        """Build citation network from document references"""
        network = {}
        for doc_name, doc_info in self.metadata["files"].items():
            if "references" in doc_info:
                network[doc_name] = doc_info["references"]
        return network

    def _get_equation_context(self, doc_name: str, equation: str) -> str:
        """Get surrounding text context for an equation"""
        try:
            txt_path = self.store_path / f"{doc_name}.txt"
            if txt_path.exists():
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Find equation position and extract surrounding context
                    pos = content.find(equation)
                    if pos >= 0:
                        start = max(0, pos - 200)
                        end = min(len(content), pos + len(equation) + 200)
                        return content[start:end].strip()
        except Exception as e:
            logger.error(f"Error getting equation context: {e}")
        return ""

    def analyze_equations(self) -> Dict[str, Any]:
        """Analyze equations across all documents"""
        stats = {
            "total_equations": 0,
            "documents_with_equations": 0,
            "equation_types": {
                "algebraic": 0,
                "differential": 0,
                "matrix": 0,
                "statistical": 0
            }
        }
        
        for doc_info in self.metadata["files"].values():
            if "equations" in doc_info and doc_info["equations"]:
                stats["documents_with_equations"] += 1
                stats["total_equations"] += len(doc_info["equations"])
                
                # Classify equations
                for _, eq in doc_info["equations"]:
                    if any(term in eq.lower() for term in ["\\frac{d", "\\partial"]):
                        stats["equation_types"]["differential"] += 1
                    elif any(term in eq.lower() for term in ["\\matrix", "\\begin{bmatrix}"]):
                        stats["equation_types"]["matrix"] += 1
                    elif any(term in eq.lower() for term in ["\\sum", "\\prod", "\\mathbb{E}", "\\mathbb{P}"]):
                        stats["equation_types"]["statistical"] += 1
                    else:
                        stats["equation_types"]["algebraic"] += 1
        
        return stats