import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import fitz
import requests
from PyPDF2 import PdfReader
from termcolor import colored
from .equation_metadata import Equation

logger = logging.getLogger(__name__)

# Enums and Constants
class ValidationLevel(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"

class CitationStyle(str, Enum):
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"

# Base Classes
@dataclass
class Author:
    """Represents an author with structured information."""
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Author':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'affiliation': self.affiliation,
            'email': self.email
        }

@dataclass
class Reference:
    """Represents a bibliographic reference."""
    raw_text: str
    title: Optional[str] = None
    authors: List[Author] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Reference':
        data = data.copy()
        if 'authors' in data:
            data['authors'] = [Author.from_dict(a) for a in data['authors']]
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'raw_text': self.raw_text,
            'title': self.title,
            'authors': [author.to_dict() for author in self.authors],
            'year': self.year,
            'doi': self.doi,
            'venue': self.venue
        }

@dataclass
class Citation:
    """Represents a citation within the text."""
    text: str
    references: List[Reference] = field(default_factory=list)  # Now a list of references
    context: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Citation':
        data = data.copy()
        if 'references' in data and data['references']:
            data['references'] = [Reference.from_dict(ref) for ref in data['references']]
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'text': self.text,
            'references': [ref.to_dict() for ref in self.references] if self.references else [],
            'context': self.context
        }

@dataclass
class ValidationResult:
    """Result of reference validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

# Main Classes
@dataclass
class AcademicMetadata:
    """Represents academic metadata extracted from a document"""
    doc_id: str
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    abstract: str = ""
    references: List[Reference] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    identifier: str = ""
    identifier_type: str = ""
    year: Optional[int] = None
    journal: str = ""
    source: str = ""
    validation_info: Dict[str, Any] = field(default_factory=dict)
    extraction_method: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format"""
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'authors': [author.to_dict() for author in self.authors],
            'abstract': self.abstract,
            'references': [ref.to_dict() for ref in self.references],
            'equations': [eq.to_dict() for eq in self.equations],
            'citations': [cit.to_dict() for cit in self.citations],
            'identifier': self.identifier,
            'identifier_type': self.identifier_type,
            'year': self.year,
            'journal': self.journal,
            'source': self.source,
            'validation_info': self.validation_info,
            'extraction_method': self.extraction_method
        }

class ReferenceValidator:
    """Validates academic references based on specified criteria."""
    def __init__(self, level: ValidationLevel = ValidationLevel.STANDARD):
        self.level = level
    
    def validate(self, reference: Reference) -> ValidationResult:
        errors = []
        warnings = []
        
        # Basic validation
        if not reference.raw_text:
            errors.append("Reference text is empty")
        
        if self.level in [ValidationLevel.STANDARD, ValidationLevel.STRICT]:
            # Standard validation
            if not reference.title:
                warnings.append("Missing title")
            if not reference.authors:
                warnings.append("Missing authors")
            if not reference.year:
                warnings.append("Missing year")
            
            if self.level == ValidationLevel.STRICT:
                # Strict validation
                if not reference.doi:
                    warnings.append("Missing DOI")
                if not reference.venue:
                    warnings.append("Missing venue")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class PDFMetadataExtractor:
    """Handles PDF-specific metadata extraction"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _debug_print(self, message: str, color: str = "blue") -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(colored(f"[DEBUG] {message}", color))

    def extract_from_pdf(self, pdf_path: str) -> Optional[Tuple[str, List[Author], str, str]]:
        """Extract metadata directly from PDF using multiple methods."""
        self._debug_print(f"Attempting to extract metadata from PDF: {pdf_path}")
        
        try:
            # Try PyMuPDF (fitz) first
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            self._debug_print(f"PyMuPDF metadata: {metadata}")
            
            # Try to get DOI
            doi = None
            for page in doc:
                text = page.get_text()
                doi_match = re.search(r'10\.\d{4,}/[-._;()/:\w]+', text)
                if doi_match:
                    doi = doi_match.group()
                    self._debug_print(f"Found DOI: {doi}")
                    break
            
            doc.close()
            
            if doi:
                return self._try_crossref_extraction(doi)
            
            # Fallback to PDF metadata
            if metadata:
                return self._extract_from_metadata(metadata)
            
            # Try PyPDF2 as last resort
            return self._try_pypdf2_extraction(pdf_path)
            
        except Exception as e:
            self._debug_print(f"Error extracting PDF metadata: {str(e)}", "red")
            return None

    def _try_crossref_extraction(self, doi: str) -> Optional[Tuple[str, List[Author], str, str]]:
        """Try to extract metadata from CrossRef using DOI."""
        try:
            response = requests.get(f"https://api.crossref.org/works/{doi}")
            if response.status_code == 200:
                data = response.json()['message']
                self._debug_print("Successfully retrieved CrossRef data")
                print(colored("✓ Using CrossRef API metadata", "green"))
                
                # Extract title
                title = data.get('title', [None])[0]
                
                # Extract authors
                authors = []
                for author in data.get('author', []):
                    given = author.get('given', '')
                    family = author.get('family', '')
                    full_name = f"{given} {family}".strip()
                    if full_name:
                        authors.append(Author(
                            full_name=full_name,
                            first_name=given,
                            last_name=family
                        ))
                
                # Extract abstract
                abstract = data.get('abstract', '')
                
                return title, authors, abstract, doi
        except Exception as e:
            self._debug_print(f"CrossRef API error: {str(e)}", "yellow")
        return None

    def _extract_from_metadata(self, metadata: Dict) -> Optional[Tuple[str, List[Author], str, str]]:
        """Extract metadata from PDF metadata dictionary."""
        title = metadata.get('title', '')
        author_str = metadata.get('author', '')
        authors = []
        
        if title or author_str:  # Only use if we got something useful
            print(colored("✓ Using PyPDF2 metadata", "green"))
            
            if author_str:
                # Split authors on common separators
                for name in re.split(r'[,;&]', author_str):
                    name = name.strip()
                    if name:
                        parts = name.split()
                        if len(parts) > 1:
                            authors.append(Author(
                                full_name=name,
                                first_name=parts[0],
                                last_name=parts[-1]
                            ))
            
            return title, authors, metadata.get('subject', ''), None
        return None

    def _try_pypdf2_extraction(self, pdf_path: str) -> Optional[Tuple[str, List[Author], str, str]]:
        """Try to extract metadata using PyPDF2."""
        try:
            reader = PdfReader(pdf_path)
            if reader.metadata:
                meta = reader.metadata
                title = meta.get('/Title', '')
                author_str = meta.get('/Author', '')
                
                if title or author_str:
                    print(colored("✓ Using PyPDF2 metadata", "green"))
                    authors = []
                    
                    if author_str:
                        for name in re.split(r'[,;&]', author_str):
                            name = name.strip()
                            if name:
                                parts = name.split()
                                if len(parts) > 1:
                                    authors.append(Author(
                                        full_name=name,
                                        first_name=parts[0],
                                        last_name=parts[-1]
                                    ))
                    
                    return title, authors, meta.get('/Subject', ''), None
        except Exception as e:
            self._debug_print(f"PyPDF2 extraction error: {str(e)}", "yellow")
        return None

    def extract_metadata(self, text: str, doc_id: str, pdf_path: Optional[str] = None, existing_metadata: Dict = None) -> AcademicMetadata:
        """Extract academic metadata from text and PDF, reusing existing metadata if available"""
        try:
            # If we have existing metadata from arXiv or DOI, use it but add references
            if existing_metadata and existing_metadata.get('source') in ['arxiv', 'crossref']:
                print(colored(f"✓ Using existing {existing_metadata['source']} metadata", "green"))
                
                # Convert authors to proper Author objects
                authors = []
                for author_data in existing_metadata.get('authors', []):
                    if isinstance(author_data, dict):
                        given = author_data.get('given', '')
                        family = author_data.get('family', '')
                        full_name = f"{given} {family}".strip()
                        authors.append(Author(
                            full_name=full_name,
                            first_name=given,
                            last_name=family
                        ))
                    elif isinstance(author_data, Author):
                        authors.append(author_data)
                
                # Extract references section from text
                references_text = self._extract_references_section(text)
                if references_text and self.anystyle_available:
                    print(colored("→ Extracting references with Anystyle...", "blue"))
                    references = self._parse_references(references_text)
                    if references:
                        print(colored(f"✓ Found {len(references)} references", "green"))
                        return AcademicMetadata(
                            doc_id=doc_id,
                            title=existing_metadata.get('title', ''),
                            authors=authors,
                            abstract=existing_metadata.get('abstract', ''),
                            references=references
                        )
                
                # If no references found, still return metadata
                return AcademicMetadata(
                    doc_id=doc_id,
                    title=existing_metadata.get('title', ''),
                    authors=authors,
                    abstract=existing_metadata.get('abstract', '')
                )
            
            # Extract metadata from scratch
            title = self._extract_title(text)
            authors = self._extract_authors(text)
            abstract = self._extract_abstract(text)
            references = []
            
            # Extract references if available
            references_text = self._extract_references_section(text)
            if references_text and self.anystyle_available:
                print(colored("→ Extracting references with Anystyle...", "blue"))
                references = self._parse_references(references_text)
                if references:
                    print(colored(f"✓ Found {len(references)} references", "green"))
            
            # Create and return AcademicMetadata object
            return AcademicMetadata(
                doc_id=doc_id,
                title=title or '',
                authors=authors,
                abstract=abstract or '',
                references=references
            )
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting metadata: {str(e)}", "red"))
            # Return empty metadata object on error
            return AcademicMetadata(doc_id=doc_id)

    def _parse_from_text(self, text: str) -> AcademicMetadata:
        """Parse metadata from text content."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if self.debug:
            print(colored("\nFirst 20 lines:", "blue"))
            for i, line in enumerate(lines[:20]):
                print(colored(f"Line {i}: {line}", "cyan"))
        
        # Extract title - handle markdown headers and common patterns
        title = "Untitled Document"
        title_index = -1
        subtitle = None
        
        # Common patterns to skip
        skip_patterns = [
            'open', '## open', '## **open**',
            'contents lists available',
            'image', 'figure', 'table',
            'received:', 'accepted:', 'published:', 'doi:', '@', 'university',
            'available online', 'sciencedirect', 'elsevier',
            'journal', 'volume', 'issue'
        ]
        
        self._debug_print("\nLooking for markdown title...")
        # First try to find a markdown title with #
        for i, line in enumerate(lines):
            if line.startswith(('#', '##')):
                clean_line = re.sub(r'[#*]', '', line).strip()
                self._debug_print(f"Found markdown line {i}: {line}")
                
                if any(skip in clean_line.lower() for skip in skip_patterns):
                    self._debug_print("Skipping - matches skip pattern", "yellow")
                    continue
                    
                if re.match(r'^[\d\.]+\s', clean_line):
                    self._debug_print("Skipping - appears to be section number", "yellow")
                    continue
                
                title = clean_line
                title_index = i
                # Check for subtitle in italics on next line
                if i + 1 < len(lines) and lines[i + 1].startswith('*'):
                    subtitle = re.sub(r'[*]', '', lines[i + 1]).strip()
                self._debug_print("Selected as title!", "green")
                break
        
        # If no markdown title found, look for other title patterns
        if title_index == -1:
            self._debug_print("\nNo markdown title found, looking for title-like text...")
            for i, line in enumerate(lines[:20]):
                self._debug_print(f"\nAnalyzing line {i}: {line}")
                
                # Skip lines that are too short or too long
                if len(line) < 20 or len(line) > 250:
                    self._debug_print("Skipping - length out of range", "yellow")
                    continue
                    
                # Skip lines that match skip patterns
                if any(skip in line.lower() for skip in skip_patterns):
                    self._debug_print("Skipping - matches skip pattern", "yellow")
                    continue
                    
                # Skip lines that look like image descriptions
                if re.match(r'^(?:image|figure|fig\.?)\s+\d', line.lower()):
                    self._debug_print("Skipping - appears to be image description")
                    continue
                    
                # Skip lines that are dates or metadata
                if re.match(r'^(?:\d{1,2}\s+\w+\s+\d{4}|doi:|https?://)', line.lower()):
                    self._debug_print("Skipping - appears to be date or metadata")
                    continue
                
                # Check title criteria
                if not line[0].isupper():
                    self._debug_print("Skipping - doesn't start with capital letter", "yellow")
                    continue
                    
                if len(line.split()) <= 3:
                    self._debug_print("Skipping - too few words")
                    continue
                    
                digit_ratio = sum(c.isdigit() for c in line) / len(line)
                if digit_ratio >= 0.2:
                    self._debug_print("Skipping - too many digits")
                    continue
                    
                special_char_ratio = sum(not c.isalnum() and not c.isspace() for c in line) / len(line)
                if special_char_ratio >= 0.1:
                    self._debug_print("Skipping - too many special characters")
                    continue
                
                title = line
                title_index = i
                self._debug_print("Selected as title!", "green")
                break
        
        # Add subtitle to title if found
        if subtitle:
            title = f"{title}: {subtitle}"
        
        self._debug_print(f"\nFinal title: {title}", "green")
        
        # Extract authors - look for patterns after title
        authors = []
        if title_index != -1:
            self._debug_print("\nLooking for authors after title...")
            # Look at next few lines for authors
            for i in range(title_index + 1, min(title_index + 5, len(lines))):
                line = lines[i]
                self._debug_print(f"\nAnalyzing line {i}: {line}")
                
                # Skip empty lines and non-author content
                if not line or any(skip in line.lower() for skip in ['abstract', 'introduction', 'keywords', 'received']):
                    self._debug_print("Skipping - empty or non-author content", "yellow")
                    continue
                
                # Look for lines with author-like patterns
                if (',' in line or ' & ' in line or ' and ' in line.lower() or '**' in line or 'M.D.' in line):
                    self._debug_print("Found potential author line")
                    # Clean the line
                    author_line = line.replace('**', '').strip()
                    
                    # Handle affiliations marked with numbers
                    author_line = re.sub(r'\d+\s*$', '', author_line)
                    author_line = re.sub(r'\s*,\s*M\.D\.', '', author_line)
                    author_line = re.sub(r'\s*,\s*Ph\.D\.', '', author_line)
                    author_line = re.sub(r'\s*,\s*M\.P\.H\.', '', author_line)
                    
                    # Split on common separators
                    for sep in [' and ', ' & ', ',']:
                        author_line = author_line.replace(sep, '|')
                    author_names = [name.strip() for name in author_line.split('|') if name.strip()]
                    
                    self._debug_print(f"Split into names: {author_names}")
                    
                    for name in author_names:
                        if len(name) < 3:
                            self._debug_print(f"Skipping '{name}' - too short", "yellow")
                            continue
                            
                        if '@' in name:
                            self._debug_print(f"Skipping '{name}' - contains email", "yellow")
                            continue
                            
                        if any(word in name.lower() for word in ['university', 'department', 'division']):
                            self._debug_print(f"Skipping '{name}' - looks like institution", "yellow")
                            continue
                        
                        # Clean the name
                        name = re.sub(r'[\(\)\[\]\{\}\d]', '', name).strip()
                        # Remove degrees and titles
                        name = re.sub(r'\s*(?:M\.D\.|Ph\.D\.|M\.P\.H\.|Professor|Dr\.|Prof\.)\s*', '', name)
                        parts = [p for p in name.split() if len(p) > 1]
                        
                        if parts:
                            author = Author(
                                full_name=name,
                                first_name=parts[0],
                                last_name=parts[-1]
                            )
                            authors.append(author)
                            self._debug_print(f"Added author: {author.full_name}", "green")
                    
                    if authors:  # If we found authors, stop looking
                        break

        # Extract abstract
        abstract = ""
        abstract_start = -1
        for i, line in enumerate(lines):
            # Look for abstract header
            if re.match(r'^(?:abstract|summary)[\s:]*$', line.lower()):
                abstract_start = i
                break
            # Also check for bold/markdown abstract headers
            elif re.match(r'^[\*#\s]*(?:abstract|summary)[\*\s:]*$', line.lower()):
                abstract_start = i
                break
        
        if abstract_start != -1:
            abstract_lines = []
            for line in lines[abstract_start + 1:]:
                if any(marker in line.lower() for marker in ['introduction', 'keywords', '1.', 'background']):
                    break
                if line.strip():
                    abstract_lines.append(line.strip())
            abstract = ' '.join(abstract_lines)
        
        # Extract references
        references_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^[\*#\s]*references[\*\s]*$', line.lower()):
                references_start = i
                break
        
        references = []
        if references_start != -1:
            # Skip the "References" header line
            references_text = lines[references_start + 1:]
            references = self._parse_references(references_text)
            # Remove any reference where the author's name is "References"
            references = [ref for ref in references if not (ref.authors and ref.authors[0].full_name == "References")]
        
        # Create and return AcademicMetadata object
        return AcademicMetadata(
            title=title,
            authors=authors,
            abstract=abstract,
            references=references
        )

    def _extract_references_section(self, text: str) -> Optional[str]:
        """Extract the references section from text, supporting both PDF and markdown formats"""
        try:
            lines = text.split('\n')
            references_start = -1
            references_end = len(lines)
            
            # Enhanced pattern for markdown and PDF formats
            ref_pattern = r'^[\*#\s]*(?:references|bibliography|works cited|citations)[\*\s]*$'
            end_pattern = r'^[\*#\s]*(?:appendix|acknowledgments?|supplementary|notes?|about|author)[\*\s]*$'
            
            # Find references section start
            for i, line in enumerate(lines):
                if re.match(ref_pattern, line.lower()):
                    references_start = i + 1  # Skip the header
                    break
            
            if references_start == -1:
                return None
            
            # Find references section end (next major section or end of file)
            for i in range(references_start, len(lines)):
                if re.match(end_pattern, lines[i].lower()):
                    references_end = i
                    break
                # Also stop at markdown horizontal rules
                if re.match(r'^[\s]*[-*_]{3,}[\s]*$', lines[i]):
                    references_end = i
                    break
                    
            references_text = '\n'.join(lines[references_start:references_end])
            if not references_text.strip():
                return None
                
            print(colored("✓ Found references section", "green"))
            return references_text
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting references section: {str(e)}", "yellow"))
            return None

    def _parse_references(self, text: str) -> List[Reference]:
        """Parse references using Anystyle CLI with enhanced error handling"""
        references = []
        if not self.anystyle_available:
            print(colored("⚠️ Anystyle not available - skipping reference parsing", "yellow"))
            return references
            
        try:
            # Write references to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('\n'.join(text) if isinstance(text, list) else text)
                f.flush()
                temp_path = f.name
                
                try:
                    # Run anystyle parse command
                    cmd = ['anystyle', '--format', 'json', 'parse', temp_path]
                    print(colored(f"→ Running Anystyle: {' '.join(cmd)}", "blue"))
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout:
                        try:
                            parsed_refs = json.loads(result.stdout)
                            for ref in parsed_refs:
                                try:
                                    # Handle date/year parsing
                                    year = None
                                    if 'date' in ref:
                                        try:
                                            date_str = str(ref['date'][0]) if isinstance(ref['date'], list) else str(ref['date'])
                                            year_match = re.search(r'\d{4}', date_str)
                                            if year_match:
                                                year = int(year_match.group())
                                        except (ValueError, TypeError, IndexError) as e:
                                            print(colored(f"⚠️ Could not parse year from date: {ref.get('date')} - {e}", "yellow"))
                                    
                                    # Create reference object
                                    reference = Reference(
                                        raw_text=ref.get('original', ''),
                                        title=ref.get('title', [None])[0] if isinstance(ref.get('title', []), list) else ref.get('title'),
                                        authors=self._parse_authors(ref.get('author', [])),
                                        year=year,
                                        doi=ref.get('doi', [None])[0] if isinstance(ref.get('doi', []), list) else ref.get('doi'),
                                        venue=ref.get('container-title', [None])[0] if isinstance(ref.get('container-title', []), list) else ref.get('container-title')
                                    )
                                    references.append(reference)
                                except Exception as e:
                                    print(colored(f"⚠️ Error parsing individual reference: {str(e)}", "yellow"))
                                    continue
                                    
                        except json.JSONDecodeError as e:
                            print(colored(f"⚠️ Error decoding Anystyle JSON output: {str(e)}", "yellow"))
                    else:
                        print(colored(f"⚠️ Anystyle command failed: {result.stderr}", "yellow"))
                        
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
                        
        except Exception as e:
            print(colored(f"⚠️ Error running Anystyle: {str(e)}", "yellow"))
            
        return references

    def _extract_authors(self, authors_data: List[Any]) -> List[Author]:
        """Parse authors with improved filtering for addresses and institutions"""
        authors = []
        
        # Common address/institution keywords to filter out
        address_keywords = {'university', 'department', 'institute', 'school', 'college', 
                           'street', 'road', 'ave', 'boulevard', 'blvd', 'usa', 'uk'}
        
        for author_data in authors_data:
            try:
                if isinstance(author_data, dict):
                    full_name = f"{author_data.get('given', '')} {author_data.get('family', '')}".strip()
                else:
                    full_name = str(author_data).strip()
                
                # Skip if empty or looks like an address
                if not full_name or any(keyword in full_name.lower() for keyword in address_keywords):
                    continue
                    
                # Basic name parsing
                parts = full_name.split()
                first_name = parts[0] if parts else None
                last_name = parts[-1] if len(parts) > 1 else None
                
                authors.append(Author(
                    full_name=full_name,
                    first_name=first_name,
                    last_name=last_name
                ))
            except Exception as e:
                print(colored(f"⚠️ Error parsing author: {str(e)}", "yellow"))
                continue
            
        return authors

    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from text using common patterns."""
        try:
            lines = text.split('\n')
            abstract = ""
            abstract_start = -1
            
            # Look for abstract header
            for i, line in enumerate(lines):
                # Look for abstract header
                if re.match(r'^(?:abstract|summary)[\s:]*$', line.lower()):
                    abstract_start = i
                    break
                # Also check for bold/markdown abstract headers
                elif re.match(r'^[\*#\s]*(?:abstract|summary)[\*\s:]*$', line.lower()):
                    abstract_start = i
                    break
            
            if abstract_start != -1:
                abstract_lines = []
                for line in lines[abstract_start + 1:]:
                    if any(marker in line.lower() for marker in ['introduction', 'keywords', '1.', 'background']):
                        break
                    if line.strip():
                        abstract_lines.append(line.strip())
                abstract = ' '.join(abstract_lines)
                
                if abstract:
                    print(colored("✓ Found abstract", "green"))
                    return abstract
            
            print(colored("⚠️ No abstract found", "yellow"))
            return None
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting abstract: {str(e)}", "yellow"))
            return None

    def _extract_citations(self, text: str) -> List[Citation]:
        """Extract citations from text"""
        citations = []
        try:
            # Common citation patterns
            patterns = [
                r'\[(\d+(?:,\s*\d+)*)\]',  # [1] or [1,2,3]
                r'\[([A-Za-z-]+\s*(?:,\s*[A-Za-z-]+)*)\]',  # [Smith] or [Smith,Jones]
                r'\(([^)]+?(?:\d{4})[^)]*)\)',  # (Smith 2020) or (Smith and Jones 2020)
            ]
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                for pattern in patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        citation_text = match.group(0)
                        
                        # Get context (surrounding lines)
                        start = max(0, i-1)
                        end = min(len(lines), i+2)
                        context = '\n'.join(lines[start:end])
                        
                        # Create Citation object
                        citation = Citation(
                            text=citation_text,
                            context=context
                        )
                        citations.append(citation)
                        
            return citations
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting citations: {str(e)}", "yellow"))
            return []