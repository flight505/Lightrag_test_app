from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import json
from threading import RLock
from src.academic_metadata import MetadataExtractor
from termcolor import colored
from src.pdf_converter import MarkerConverter
from src.config_manager import ConfigManager
import logging
import pdf2doi
from crossref.restful import Works
import streamlit as st

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file preprocessing and tracking with enhanced equation support"""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize FileProcessor with configuration"""
        self.config_manager = config_manager
        self.marker_converter = None  # Lazy initialization
        self.metadata_extractor = MetadataExtractor()
        self.metadata = {}
        self.metadata_lock = RLock()
        self.store_path = None
        self.metadata_file = None
        self.works = Works()  # Initialize crossref client
        logger.info("FileProcessor initialized")

    def _ensure_marker_initialized(self):
        """Ensure Marker is initialized when needed"""
        if self.marker_converter is None:
            print(colored("→ Initializing Marker converter...", "blue"))
            self.marker_converter = MarkerConverter()
            print(colored("✓ Marker initialized", "green"))

    def _convert_pdf_with_marker(self, pdf_path: str) -> Optional[str]:
        """Convert PDF to text using Marker for semantic preservation"""
        self._ensure_marker_initialized()
        text_content = self.marker_converter.extract_text(str(pdf_path))
        if text_content:
            print(colored("✓ Text extracted with semantic structure preserved", "green"))
            return text_content
        print(colored(f"❌ No text extracted from {Path(pdf_path).name}", "red"))
        return None

    @st.cache_data(show_spinner=False)
    def _extract_metadata_with_doi(_self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using DOI lookup"""
        print(colored("\n=== Starting DOI-based Metadata Extraction ===", "blue"))
        try:
            # Try pdf2doi first
            print(colored("→ Attempting pdf2doi extraction...", "blue"))
            result = pdf2doi.pdf2doi(file_path)
            
            # Handle pdf2doi result dictionary
            if isinstance(result, dict):
                identifier = result.get('identifier')
                identifier_type = result.get('identifier_type', '').lower()
                validation_info = result.get('validation_info')
                method = result.get('method')
                
                if not identifier:
                    print(colored("⚠️ No identifier found in PDF", "yellow"))
                    return None
                    
                print(colored(f"✓ Found {identifier_type}: {identifier} (method: {method})", "green"))
                
                # Check if it's an arXiv identifier
                if "arxiv" in identifier.lower():
                    print(colored("→ arXiv identifier detected, fetching from arXiv API...", "blue"))
                    try:
                        # Extract just the raw arXiv ID number
                        arxiv_id = identifier.lower()
                        if '/' in arxiv_id:
                            arxiv_id = arxiv_id.split('/')[-1]
                        if 'arxiv.' in arxiv_id:
                            arxiv_id = arxiv_id.split('arxiv.')[-1]
                        if ':' in arxiv_id:
                            arxiv_id = arxiv_id.split(':')[-1]
                        arxiv_id = arxiv_id.strip()
                        
                        print(colored(f"→ Querying arXiv API with ID: {arxiv_id}", "blue"))
                        
                        import arxiv
                        search = arxiv.Search(id_list=[arxiv_id])
                        paper = next(search.results())
                        
                        # Process authors
                        authors = []
                        for author in paper.authors:
                            name_parts = str(author).split()
                            if len(name_parts) > 0:
                                given = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else ''
                                family = name_parts[-1]
                                authors.append({
                                    'given': given,
                                    'family': family,
                                    'full_name': str(author)
                                })
                        
                        metadata = {
                            'title': paper.title,
                            'authors': authors,
                            'abstract': paper.summary,
                            'identifier': arxiv_id,
                            'identifier_type': 'arxiv',
                            'year': paper.published.year if paper.published else None,
                            'categories': paper.categories if hasattr(paper, 'categories') else [],
                            'source': 'arxiv',
                            'validation_info': validation_info,
                            'extraction_method': method
                        }
                        
                        print(colored("✓ arXiv metadata extracted successfully", "green"))
                        return metadata
                        
                    except Exception as e:
                        print(colored(f"⚠️ arXiv API error: {str(e)}", "yellow"))
                        return None
                
                # If not arXiv, try Crossref
                print(colored("→ Using Crossref for DOI lookup...", "blue"))
                try:
                    work = _self.works.doi(identifier)
                    if work:
                        authors = []
                        for author in work.get('author', []):
                            try:
                                given = author.get('given', '').strip()
                                family = author.get('family', '').strip()
                                if given or family:
                                    authors.append({
                                        'given': given,
                                        'family': family,
                                        'full_name': f"{given} {family}".strip()
                                    })
                            except Exception as e:
                                print(colored(f"⚠️ Error processing Crossref author: {str(e)}", "yellow"))
                                continue
                        
                        metadata = {
                            'title': work.get('title', [None])[0],
                            'authors': authors,
                            'identifier': identifier,
                            'identifier_type': 'doi',
                            'year': work.get('published-print', {}).get('date-parts', [[None]])[0][0],
                            'journal': work.get('container-title', [None])[0],
                            'source': 'crossref',
                            'validation_info': validation_info,
                            'extraction_method': method
                        }
                        
                        print(colored("✓ Crossref metadata extracted successfully", "green"))
                        return metadata
                    else:
                        print(colored("⚠️ Crossref lookup failed - no metadata found", "yellow"))
                except Exception as e:
                    print(colored(f"⚠️ Crossref API error: {str(e)}", "yellow"))
                    return None
                
            else:
                print(colored("⚠️ Invalid pdf2doi result format", "yellow"))
                
        except Exception as e:
            logger.warning(f"DOI extraction failed: {str(e)}")
            print(colored(f"⚠️ DOI extraction failed: {str(e)}", "yellow"))
        
        print(colored("⚠️ DOI-based extraction failed", "yellow"))
        return None

    def process_file(self, file_path: str, progress_callback: Optional[Callable] = None) -> Optional[Dict[str, Any]]:
        """Process a file and extract metadata"""
        try:
            print(colored("\n=== Starting File Processing ===", "blue"))
            
            # Validate file
            print(colored("→ Validating file...", "blue"))
            if not self.config_manager.config.validate_file(file_path):
                print(colored("⚠️ File validation failed", "yellow"))
                return None
            print(colored("✓ File validation successful", "green"))
            
            # Extract text content
            print(colored("\n=== Extracting Text Content ===", "blue"))
            text_content = self._convert_pdf_with_marker(file_path)
            if not text_content:
                print(colored("❌ Failed to extract text content", "red"))
                return None
                
            if progress_callback:
                progress_callback(0.5)
            
            # Extract metadata
            print(colored("\n=== Extracting Metadata ===", "blue"))
            metadata = None
            try:
                metadata = self._extract_metadata_with_doi(file_path)
                if metadata:
                    print(colored(f"✓ Using metadata from {metadata.get('source', 'unknown')}", "green"))
                    
                    # Extract references using Anystyle
                    print(colored("\n=== Extracting References with Anystyle ===", "blue"))
                    try:
                        doc_id = Path(file_path).stem
                        academic_metadata = self.metadata_extractor.extract_metadata(text_content, doc_id=doc_id)
                        if academic_metadata and hasattr(academic_metadata, 'references') and academic_metadata.references:
                            # Convert references to list of dicts, handling None values
                            ref_dicts = []
                            for ref in academic_metadata.references:
                                ref_dict = {
                                    'raw_text': ref.raw_text if hasattr(ref, 'raw_text') else '',
                                    'title': ref.title if hasattr(ref, 'title') else None,
                                    'authors': [{'full_name': a.full_name} for a in ref.authors] if hasattr(ref, 'authors') and ref.authors else [],
                                    'year': ref.year if hasattr(ref, 'year') else None,
                                    'doi': ref.doi if hasattr(ref, 'doi') else None,
                                    'venue': ref.venue if hasattr(ref, 'venue') else None
                                }
                                ref_dicts.append(ref_dict)
                            metadata['references'] = ref_dicts
                            print(colored(f"✓ Extracted {len(ref_dicts)} references with Anystyle", "green"))
                        else:
                            print(colored("⚠️ No references found by Anystyle", "yellow"))
                    except Exception as e:
                        print(colored(f"⚠️ Anystyle reference extraction failed: {str(e)}", "yellow"))
                    
                    # Save metadata to file
                    metadata_file = Path(file_path).parent / f"{Path(file_path).stem}_metadata.json"
                    try:
                        with open(metadata_file, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, indent=2, ensure_ascii=False)
                        print(colored(f"✓ Metadata saved to {metadata_file}", "green"))
                    except Exception as e:
                        print(colored(f"⚠️ Error saving metadata: {str(e)}", "yellow"))
                        
            except Exception as e:
                print(colored(f"⚠️ DOI metadata extraction failed: {str(e)}", "yellow"))
            
            if progress_callback:
                progress_callback(0.75)
            
            # Save text content
            print(colored("\n=== Saving Text Content ===", "blue"))
            text_file = Path(file_path).with_suffix('.txt')
            try:
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                print(colored(f"✓ Text saved to {text_file}", "green"))
            except Exception as e:
                print(colored(f"⚠️ Error saving text: {str(e)}", "yellow"))
            
            if progress_callback:
                progress_callback(1.0)
                
            print(colored("\n=== Processing Complete ===", "green"))
            return {
                'text': text_content,
                'metadata': metadata
            }
            
        except Exception as e:
            print(colored(f"❌ Error processing file: {str(e)}", "red"))
            return None

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
            for ext in [".txt", ".md"]:
                for file_path in Path(self.store_path).glob(f"*{ext}"):
                    if file_path.stem not in pdfs:
                        try:
                            file_path.unlink()
                            removed_files.append(str(file_path))
                            print(colored(f"✓ Removed orphaned file: {file_path.name}", "green"))
                        except Exception as e:
                            print(colored(f"⚠️ Error removing {file_path.name}: {str(e)}", "yellow"))
            
            # Check for orphaned metadata files
            for file_path in Path(self.store_path).glob("*_metadata.json"):
                pdf_stem = file_path.stem.replace("_metadata", "")
                if pdf_stem not in pdfs:
                    try:
                        file_path.unlink()
                        removed_files.append(str(file_path))
                        print(colored(f"✓ Removed orphaned metadata: {file_path.name}", "green"))
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