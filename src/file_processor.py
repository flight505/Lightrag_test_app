from typing import Dict, List, Any, Union, Optional, Callable
from pathlib import Path
from datetime import datetime
import json
import os
from threading import RLock
from src.academic_metadata import MetadataExtractor, AcademicMetadata
from termcolor import colored
from dataclasses import dataclass
from src.pdf_converter import MarkerConverter, PyMuPDFConverter
from src.config_manager import ConfigManager
import logging
import pdf2doi
from crossref.restful import Works
from scholarly import scholarly
import fitz
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize FileProcessor with configuration"""
        self.config_manager = config_manager
        self.marker_converter = None
        self.pymupdf_converter = PyMuPDFConverter()  # Fallback converter
        self.metadata_extractor = MetadataExtractor()
        self.metadata = {}
        self.metadata_lock = RLock()
        self.store_path = None
        self.metadata_file = None
        self.works = Works()  # Initialize crossref client
        logger.info("FileProcessor initialized")

    def _extract_metadata_with_doi(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using DOI lookup"""
        try:
            # Try pdf2doi first
            result = pdf2doi.pdf2doi(file_path)
            if isinstance(result, dict) and 'identifier' in result:
                doi = result['identifier']
            else:
                doi = result
                
            if doi:
                print(colored(f"✓ Found DOI: {doi}", "green"))
                # Get BibTeX from crossref
                work = self.works.doi(doi)
                if work:
                    authors = []
                    for author in work.get('author', []):
                        authors.append({
                            'given': author.get('given', ''),
                            'family': author.get('family', ''),
                            'full_name': f"{author.get('given', '')} {author.get('family', '')}"
                        })
                    
                    return {
                        'title': work.get('title', [None])[0],
                        'authors': authors,
                        'doi': doi,
                        'year': work.get('published-print', {}).get('date-parts', [[None]])[0][0],
                        'journal': work.get('container-title', [None])[0],
                        'source': 'crossref'
                    }
        except Exception as e:
            logger.warning(f"DOI extraction failed: {str(e)}")
            print(colored(f"⚠️ DOI extraction failed: {str(e)}", "yellow"))
        return None

    def _extract_metadata_fallback(self, file_path: str, text: str) -> Dict[str, Any]:
        """Extract metadata using PyPDF2/PyMuPDF and scholarly"""
        metadata = {}
        
        try:
            # Try PyMuPDF first
            doc = fitz.open(file_path)
            metadata = doc.metadata
            doc.close()
            
            if not metadata:
                # Fallback to PyPDF2
                reader = PdfReader(file_path)
                metadata = reader.metadata
                if metadata:
                    # Convert PyPDF2 metadata format
                    metadata = {k[1:].lower(): v for k, v in metadata.items() if k.startswith('/')}
            
            # Try to enhance with scholarly
            if metadata.get('title'):
                try:
                    search_query = scholarly.search_pubs(metadata['title'])
                    pub = next(search_query, None)
                    if pub:
                        bib = pub.get('bib', {})
                        authors = []
                        if bib.get('author'):
                            if isinstance(bib['author'], str):
                                # Split author string
                                author_list = [a.strip() for a in bib['author'].split(' and ')]
                            else:
                                author_list = bib['author']
                                
                            for author in author_list:
                                if isinstance(author, str):
                                    authors.append({'full_name': author})
                                else:
                                    authors.append(author)
                        
                        metadata.update({
                            'title': bib.get('title', metadata.get('title')),
                            'authors': authors,
                            'year': bib.get('year', metadata.get('year')),
                            'journal': bib.get('journal', metadata.get('journal')),
                            'abstract': bib.get('abstract', ''),
                            'source': 'scholarly'
                        })
                except Exception as e:
                    logger.warning(f"Scholarly lookup failed: {str(e)}")
                    print(colored(f"⚠️ Scholarly lookup failed: {str(e)}", "yellow"))
            
        except Exception as e:
            logger.error(f"Fallback metadata extraction failed: {str(e)}")
            print(colored(f"⚠️ Fallback metadata extraction failed: {str(e)}", "yellow"))
        
        return metadata

    def _ensure_marker_initialized(self) -> bool:
        """Ensure Marker converter is initialized, return True if successful"""
        if self.marker_converter is None:
            try:
                self.marker_converter = MarkerConverter()
                logger.info("Created MarkerConverter instance")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Marker: {str(e)}")
                print(colored(f"⚠️ Failed to initialize Marker: {str(e)}", "yellow"))
                return False
        return True

    def _convert_pdf_with_marker(self, pdf_path: str) -> Optional[str]:
        """Convert PDF to text using Marker with PyMuPDF fallback"""
        try:
            # Try to initialize marker
            if self._ensure_marker_initialized():
                try:
                    # Extract text using MarkerConverter
                    text_content = self.marker_converter.extract_text(str(pdf_path))
                    if text_content:
                        print(colored("✓ Text extracted with Marker", "green"))
                        return text_content
                except Exception as e:
                    logger.warning(f"Marker text extraction failed: {str(e)}")
                    print(colored(f"⚠️ Marker extraction failed: {str(e)}", "yellow"))
            
            # Fallback to PyMuPDF
            print(colored("ℹ️ Falling back to PyMuPDF for text extraction", "blue"))
            text_content = self.pymupdf_converter.extract_text(str(pdf_path))
            if text_content:
                print(colored("✓ Text extracted with PyMuPDF", "green"))
                return text_content
            
            print(colored(f"❌ No text extracted from {Path(pdf_path).name}", "red"))
            return None
            
        except Exception as e:
            print(colored(f"❌ Error converting PDF {Path(pdf_path).name}: {str(e)}", "red"))
            return None

    def process_file(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """Process a file and extract its content and metadata"""
        try:
            # Validate file
            error = self.config_manager.validate_file(file_path)
            if error:
                print(colored(f"⚠️ File validation failed: {error}", "red"))
                return {"error": error}
            
            # Extract text first for potential use in metadata extraction
            if progress_callback:
                progress_callback("Converting PDF...")
            text = self._convert_pdf_with_marker(file_path)
            if not text:
                return {"error": "Failed to extract text from PDF"}
            
            # Save the extracted text
            text_path = Path(file_path).with_suffix('.txt')
            try:
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(colored(f"✓ Text saved to {text_path}", "green"))
            except Exception as e:
                print(colored(f"⚠️ Error saving text: {str(e)}", "yellow"))
            
            # Try DOI-based metadata extraction first
            if progress_callback:
                progress_callback("Extracting metadata...")
            metadata = self._extract_metadata_with_doi(file_path)
            
            # If DOI extraction fails, use fallback methods
            if not metadata:
                print(colored("ℹ️ No DOI found, using fallback metadata extraction", "blue"))
                metadata = self._extract_metadata_fallback(file_path, text)
            
            # Finally process academic metadata with both text and PDF
            if progress_callback:
                progress_callback("Processing academic metadata...")
            academic_metadata = self.metadata_extractor.extract_metadata(
                text=text,
                doc_id=os.path.basename(file_path),
                pdf_path=file_path,
                existing_metadata=metadata  # Pass existing metadata to avoid reprocessing
            )
            
            # Convert academic metadata to dict for storage
            academic_metadata_dict = {
                'doc_id': academic_metadata.doc_id,
                'title': academic_metadata.title,
                'authors': [author.to_dict() for author in academic_metadata.authors],
                'abstract': academic_metadata.abstract,
                'references': [ref.to_dict() for ref in academic_metadata.references],
                'equations': [eq.to_dict() for eq in academic_metadata.equations],
                'citations': [cit.to_dict() for cit in academic_metadata.citations],
                'keywords': list(academic_metadata.keywords),
                'sections': academic_metadata.sections
            }
            
            # Save metadata to file
            metadata_file = Path(file_path).with_suffix('.metadata.json')
            try:
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(academic_metadata_dict, f, indent=2)
                print(colored(f"✓ Metadata saved to {metadata_file}", "green"))
            except Exception as e:
                print(colored(f"⚠️ Error saving metadata: {str(e)}", "yellow"))
            
            # Return combined results
            return {
                "text": text,
                "metadata": metadata,
                "academic_metadata": academic_metadata_dict
            }
                
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            print(colored(f"⚠️ {error_msg}", "red"))
            return {"error": error_msg}

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file"""
        try:
            if self.metadata_file and self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading metadata: {str(e)}")
            return {}

    def set_store_path(self, store_path: str) -> None:
        """Set the store path for file processing"""
        try:
            self.store_path = Path(store_path)
            self.store_path.mkdir(parents=True, exist_ok=True)
            
            self.metadata_file = self.store_path / "metadata.json"
            self.metadata = self._load_metadata()
            
            logger.info(f"Store path set to: {store_path}")
            print(colored(f"✓ Store path set to: {store_path}", "green"))
            
        except Exception as e:
            error_msg = f"Failed to set store path: {str(e)}"
            logger.error(error_msg)
            print(colored(f"❌ {error_msg}", "red"))
            raise

    def is_supported_file(self, file_path: str) -> bool:
        """Check if the file type is supported"""
        return file_path.lower().endswith('.pdf')

    def clean_unused_files(self) -> List[str]:
        """Remove orphaned files (txt/md/metadata without corresponding PDFs)"""
        if not self.store_path:
            print(colored("⚠️ No store path set", "yellow"))
            return []
            
        removed_files = []
        try:
            # Get all PDFs as reference
            pdfs = {p.stem for p in Path(self.store_path).glob("*.pdf")}
            
            # Check for orphaned files
            for ext in [".txt", ".md", ".metadata.json"]:
                for file_path in Path(self.store_path).glob(f"*{ext}"):
                    if file_path.stem not in pdfs:
                        try:
                            file_path.unlink()
                            removed_files.append(str(file_path))
                            print(colored(f"✓ Removed orphaned file: {file_path.name}", "green"))
                        except Exception as e:
                            print(colored(f"⚠️ Error removing {file_path.name}: {str(e)}", "yellow"))
            
            if removed_files:
                print(colored(f"✓ Removed {len(removed_files)} orphaned files", "green"))
            else:
                print(colored("✓ No orphaned files found", "green"))
                
            return removed_files
            
        except Exception as e:
            print(colored(f"❌ Error cleaning unused files: {str(e)}", "red"))
            return []