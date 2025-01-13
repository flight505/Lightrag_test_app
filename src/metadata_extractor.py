from typing import Dict, Any
from termcolor import colored

class MetadataExtractor:
    def extract_metadata(self, text: str, doc_id: str, pdf_path: str = None, existing_metadata: Dict = None) -> Dict[str, Any]:
        """Extract academic metadata from text and PDF, reusing existing metadata if available"""
        try:
            # If we have existing metadata from arXiv or DOI, use it as is
            if existing_metadata and existing_metadata.get('source') in ['arxiv', 'crossref']:
                print(colored(f"✓ Using existing {existing_metadata['source']} metadata", "green"))
                return existing_metadata
            
            # Initialize with existing metadata if provided
            metadata = existing_metadata or {}
            
            # Only extract what we don't already have
            if not metadata.get('title'):
                metadata['title'] = self._extract_title(text)
            
            if not metadata.get('authors'):
                metadata['authors'] = self._extract_authors(text)
                
            if not metadata.get('abstract'):
                metadata['abstract'] = self._extract_abstract(text)
                
            if not metadata.get('references') and pdf_path:
                metadata['references'] = self._extract_references(pdf_path)
                
            if not metadata.get('citations'):
                metadata['citations'] = self._extract_citations(text)
                
            return metadata
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting metadata: {str(e)}", "red"))
            return {} 