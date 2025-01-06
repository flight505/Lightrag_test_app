from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Tuple
import json
import subprocess
import tempfile
import re
import fitz  # PyMuPDF
from PyPDF2 import PdfReader
import requests
from scholarly import scholarly
from termcolor import colored
import os
import logging

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

class EquationType(str, Enum):
    INLINE = "inline"
    DISPLAY = "display"
    DEFINITION = "definition"
    THEOREM = "theorem"

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
class Equation:
    """Represents a mathematical equation with context and metadata."""
    raw_text: str
    equation_id: str
    context: str = ""
    equation_type: EquationType = EquationType.INLINE
    symbols: Set[str] = field(default_factory=set)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Equation':
        data = data.copy()
        if 'equation_type' in data:
            data['equation_type'] = EquationType(data['equation_type'])
        if 'symbols' in data:
            data['symbols'] = set(data['symbols'])
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'raw_text': self.raw_text,
            'equation_id': self.equation_id,
            'context': self.context,
            'equation_type': self.equation_type.value,
            'symbols': list(self.symbols)
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
    """Represents academic metadata with structured information."""
    doc_id: str
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    abstract: str = ""
    references: List[Reference] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    sections: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AcademicMetadata':
        """Create AcademicMetadata from dictionary."""
        data = data.copy()
        if 'authors' in data:
            data['authors'] = [Author.from_dict(a) for a in data['authors']]
        if 'references' in data:
            data['references'] = [Reference.from_dict(r) for r in data['references']]
        if 'equations' in data:
            data['equations'] = [Equation.from_dict(e) for e in data['equations']]
        if 'citations' in data:
            data['citations'] = [Citation.from_dict(c) for c in data['citations']]
        if 'keywords' in data:
            data['keywords'] = set(data['keywords'])
        return cls(**data)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'authors': [author.to_dict() for author in self.authors],
            'abstract': self.abstract,
            'references': [ref.to_dict() for ref in self.references],
            'equations': [eq.to_dict() for eq in self.equations],
            'citations': [cit.to_dict() for cit in self.citations],
            'keywords': list(self.keywords),
            'sections': self.sections
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

    def extract_metadata(self, text: str, doc_id: str, pdf_path: Optional[str] = None) -> AcademicMetadata:
        """Extract academic metadata from document text and PDF if available."""
        if self.debug:
            print(colored("\n=== Starting Metadata Extraction ===", "blue"))
        
        metadata = None
        extraction_method = "none"
        
        # Try PDF metadata extraction first if path is provided
        if pdf_path:
            self._debug_print(f"Attempting PDF metadata extraction from: {pdf_path}")
            pdf_metadata = self.extract_metadata_from_pdf(pdf_path)
            
            if pdf_metadata:
                title, authors, abstract, doi = pdf_metadata
                self._debug_print("Successfully extracted metadata from PDF")
                
                # If we have a DOI but no abstract, try scholarly
                if doi and not abstract:
                    try:
                        search_query = scholarly.search_pubs(title)
                        pub = next(search_query)
                        if pub:
                            abstract = pub.get('bib', {}).get('abstract', '')
                            self._debug_print("Found abstract from scholarly")
                    except Exception as e:
                        self._debug_print(f"Scholarly lookup failed: {str(e)}", "yellow")
                
                # Parse references from text since they're not in PDF metadata
                references = self._parse_references(text.split('\n'))
                equations = self._extract_equations(text)
                
                metadata = AcademicMetadata(
                    title=title or "Untitled Document",
                    authors=authors or [],
                    abstract=abstract,
                    references=references,
                    equations=equations
                )
                print(colored("✓ Using PDF metadata", "green"))
        
        # Fall back to text parsing only if PDF metadata extraction failed
        if not metadata or not metadata.title or not metadata.authors:
            print(colored("⚠️ Falling back to text parsing", "yellow"))
            extraction_method = "text"
            metadata = self._parse_from_text(text)
        
        # Log final extraction method used
        print(colored(f"✓ Final metadata extraction method: {extraction_method}", "green"))
        return metadata

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
        
        # Extract equations
        equations = self._extract_equations(text)
        
        return AcademicMetadata(
            title=title,
            authors=authors,
            abstract=abstract,
            references=references,
            equations=equations
        )

    def _extract_equations(self, text: str) -> List[Equation]:
        """Extract equations from text with enhanced pattern matching."""
        equations = []
        eq_id = 1
        
        try:
            # Equation patterns
            patterns = [
                (r'\$\$(.*?)\$\$', EquationType.DISPLAY),  # Display equations
                (r'\$(.*?)\$', EquationType.INLINE),  # Inline equations
                (r'\\begin\{equation\}(.*?)\\end\{equation\}', EquationType.DISPLAY),  # Numbered equations
                (r'\\[(.*?)\\]', EquationType.DISPLAY),  # Alternative display equations
                (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', EquationType.DISPLAY),  # Align environments
                (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', EquationType.DISPLAY)  # Eqnarray environments
            ]
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                for pattern, eq_type in patterns:
                    matches = re.finditer(pattern, line, re.DOTALL)
                    for match in matches:
                        # Get equation content
                        eq_text = match.group(1).strip()
                        if not eq_text:
                            continue
                            
                        # Get context (surrounding lines)
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        context = '\n'.join(lines[start:end])
                        
                        # Extract symbols
                        symbols = self._extract_equation_symbols(eq_text)
                        
                        equations.append(Equation(
                            raw_text=eq_text,
                            equation_id=f"eq{eq_id}",
                            context=context,
                            equation_type=eq_type,
                            symbols=symbols
                        ))
                        eq_id += 1
            
            return equations
            
        except Exception as e:
            logger.error(f"Error extracting equations: {str(e)}")
            print(colored(f"⚠️ Error extracting equations: {str(e)}", "yellow"))
            return []
            
    def _extract_equation_symbols(self, equation: str) -> Set[str]:
        """Extract mathematical symbols from equation."""
        symbols = set()
        
        # Common mathematical symbols
        symbol_patterns = [
            r'\\alpha', r'\\beta', r'\\gamma', r'\\delta', r'\\epsilon',
            r'\\theta', r'\\lambda', r'\\mu', r'\\pi', r'\\sigma',
            r'\\sum', r'\\prod', r'\\int', r'\\partial', r'\\infty',
            r'\\frac', r'\\sqrt', r'\\left', r'\\right', r'\\cdot',
            r'\\mathcal', r'\\mathbf', r'\\mathrm', r'\\text'
        ]
        
        try:
            # Extract LaTeX commands
            for pattern in symbol_patterns:
                if re.search(pattern, equation):
                    symbols.add(pattern.replace('\\', ''))
            
            # Extract variable names (single letters)
            var_matches = re.findall(r'(?<=[^\\])[a-zA-Z](?![a-zA-Z])', equation)
            symbols.update(var_matches)
            
            # Extract subscripts
            subscripts = re.findall(r'_\{([^}]+)\}', equation)
            symbols.update(subscripts)
            
            return symbols
            
        except Exception as e:
            logger.warning(f"Error extracting symbols: {str(e)}")
            return set()
    
    def _parse_references(self, text: str) -> List[Reference]:
        """Parse references from text using Anystyle CLI"""
        references = []
        if not self.anystyle_available:
            return references
            
        try:
            # Write references to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
                f.write('\n'.join(text) if isinstance(text, list) else text)
                f.flush()
                
                # Run anystyle parse command
                result = subprocess.run(
                    ['anystyle', '--format', 'json', 'parse', f.name],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
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
                                    doi=ref.get('doi'),
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
                    
        except Exception as e:
            print(colored(f"⚠️ Error running Anystyle: {str(e)}", "yellow"))
            
        return references
    
    def _parse_authors(self, authors_data: List[Any]) -> List[Author]:
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

class CitationParser:
    """Handles parsing and validation of academic citations"""
    
    def __init__(self):
        # Check if anystyle is available via command line
        try:
            result = subprocess.run(['anystyle', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.anystyle_available = True
                print(colored(f"✓ Found Anystyle: {result.stdout.strip()}", "green"))
            else:
                print(colored("⚠️ Anystyle command failed", "yellow"))
                self.anystyle_available = False
        except FileNotFoundError:
            print(colored("⚠️ Anystyle not found in PATH", "yellow"))
            self.anystyle_available = False
    
    def parse_references(self, text: str) -> List[Reference]:
        """Parse references from text using Anystyle CLI"""
        references = []
        if not self.anystyle_available:
            return references
            
        try:
            # Write references to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
                f.write('\n'.join(text) if isinstance(text, list) else text)
                f.flush()
                
                # Run anystyle parse command
                result = subprocess.run(
                    ['anystyle', '--format', 'json', 'parse', f.name],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
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
                                    doi=ref.get('doi'),
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
                    
        except Exception as e:
            print(colored(f"⚠️ Error running Anystyle: {str(e)}", "yellow"))
            
        return references
    
    def _parse_authors(self, authors_data: List[Any]) -> List[Author]:
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

class EquationExtractor:
    """Handles extraction and classification of mathematical equations"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _debug_print(self, message: str, color: str = "blue") -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(colored(f"[DEBUG] {message}", color))
    
    def extract_equations(self, text: str) -> List[Equation]:
        """Extract equations from text with context."""
        equations = []
        eq_id = 1
        
        try:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if '$' in line or '\\[' in line or '\\begin{equation}' in line:
                    # Get context (surrounding lines)
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    context = '\n'.join(lines[start:end])
                    
                    # Determine equation type
                    eq_type = self._determine_equation_type(line)
                    
                    # Extract symbols
                    symbols = self._extract_symbols(line)
                    
                    equations.append(Equation(
                        raw_text=line,
                        equation_id=f"eq{eq_id}",
                        context=context,
                        equation_type=eq_type,
                        symbols=symbols
                    ))
                    eq_id += 1
            
            return equations
            
        except Exception as e:
            self._debug_print(f"Error extracting equations: {str(e)}", "red")
            return []
    
    def _determine_equation_type(self, line: str) -> EquationType:
        """Determine the type of equation based on its content and context."""
        if '\\begin{theorem}' in line or '\\begin{lemma}' in line:
            return EquationType.THEOREM
        elif '\\begin{definition}' in line:
            return EquationType.DEFINITION
        elif '\\[' in line or '\\begin{equation}' in line or '\\begin{align}' in line:
            return EquationType.DISPLAY
        else:
            return EquationType.INLINE
    
    def _extract_symbols(self, equation: str) -> Set[str]:
        """Extract mathematical symbols from equation."""
        symbols = set()
        
        # Common mathematical symbols to extract
        symbol_patterns = [
            r'\\alpha', r'\\beta', r'\\gamma', r'\\delta', r'\\epsilon',
            r'\\theta', r'\\lambda', r'\\mu', r'\\pi', r'\\sigma',
            r'\\sum', r'\\prod', r'\\int', r'\\partial', r'\\infty'
        ]
        
        try:
            for pattern in symbol_patterns:
                if re.search(pattern, equation):
                    symbols.add(pattern.replace('\\', ''))
            
            # Extract variable names (single letters)
            var_matches = re.findall(r'(?<=[^\\])[a-zA-Z](?![a-zA-Z])', equation)
            symbols.update(var_matches)
            
            return symbols
            
        except Exception as e:
            self._debug_print(f"Error extracting symbols: {str(e)}", "yellow")
            return set() 

class MetadataExtractor:
    """Extract academic metadata from documents"""
    
    def extract_metadata(self, text: str, doc_id: str, pdf_path: str = None, existing_metadata: Dict = None) -> AcademicMetadata:
        """Extract academic metadata from text and PDF"""
        try:
            # Initialize metadata
            metadata = AcademicMetadata(doc_id=doc_id)
            
            # Use existing metadata if provided
            if existing_metadata:
                metadata.title = existing_metadata.get('title', '')
                if 'authors' in existing_metadata:
                    metadata.authors = [
                        Author(
                            full_name=a.get('full_name', ''),
                            first_name=a.get('given', ''),
                            last_name=a.get('family', '')
                        )
                        for a in existing_metadata['authors']
                    ]
                metadata.abstract = existing_metadata.get('abstract', '')
            
            # Extract abstract if not in existing metadata
            if not metadata.abstract and text:
                abstract_match = re.search(r'Abstract[:\s]+(.*?)(?=\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
                if abstract_match:
                    metadata.abstract = abstract_match.group(1).strip()
            
            # Extract equations
            equations = []
            eq_id = 1
            
            # Equation patterns
            patterns = [
                (r'\$\$(.*?)\$\$', EquationType.DISPLAY),  # Display equations
                (r'\$(.*?)\$', EquationType.INLINE),  # Inline equations
                (r'\\begin\{equation\}(.*?)\\end\{equation\}', EquationType.DISPLAY),  # Numbered equations
                (r'\\[(.*?)\\]', EquationType.DISPLAY),  # Alternative display equations
                (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', EquationType.DISPLAY),  # Align environments
                (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', EquationType.DISPLAY)  # Eqnarray environments
            ]
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                for pattern, eq_type in patterns:
                    matches = re.finditer(pattern, line, re.DOTALL)
                    for match in matches:
                        # Get equation content
                        eq_text = match.group(1).strip()
                        if not eq_text:
                            continue
                            
                        # Get context (surrounding lines)
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        context = '\n'.join(lines[start:end])
                        
                        # Extract symbols
                        symbols = set()
                        symbol_patterns = [
                            r'\\alpha', r'\\beta', r'\\gamma', r'\\delta', r'\\epsilon',
                            r'\\theta', r'\\lambda', r'\\mu', r'\\pi', r'\\sigma',
                            r'\\sum', r'\\prod', r'\\int', r'\\partial', r'\\infty'
                        ]
                        
                        for sym_pattern in symbol_patterns:
                            if re.search(sym_pattern, eq_text):
                                symbols.add(sym_pattern.replace('\\', ''))
                        
                        equations.append(Equation(
                            raw_text=eq_text,
                            equation_id=f"eq{eq_id}",
                            context=context,
                            equation_type=eq_type,
                            symbols=symbols
                        ))
                        eq_id += 1
            
            metadata.equations = equations
            
            # Extract references using Anystyle
            try:
                # Create a temporary file for the text content
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as temp:
                    temp.write(text)
                    temp_path = temp.name
                
                try:
                    # Run Anystyle find command
                    cmd = ["anystyle", "--format", "json", "find", temp_path]
                    logger.info(f"Running Anystyle command: {' '.join(cmd)}")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse the JSON output
                    if result.stdout:
                        references = json.loads(result.stdout)
                        
                        # Convert to our format
                        metadata.references = []
                        for ref in references:
                            try:
                                authors = []
                                for author in ref.get('author', []):
                                    if isinstance(author, dict):
                                        authors.append(Author(
                                            full_name=f"{author.get('given', '')} {author.get('family', '')}".strip(),
                                            first_name=author.get('given', ''),
                                            last_name=author.get('family', '')
                                        ))
                                    else:
                                        authors.append(Author(full_name=str(author)))
                                
                                metadata.references.append(Reference(
                                    raw_text=ref.get('original', ''),
                                    title=ref.get('title', [None])[0] if isinstance(ref.get('title', []), list) else ref.get('title'),
                                    authors=authors,
                                    year=int(ref.get('date', [None])[0]) if ref.get('date') else None,
                                    doi=ref.get('doi', [None])[0] if isinstance(ref.get('doi', []), list) else ref.get('doi'),
                                    venue=ref.get('container-title', [None])[0] if isinstance(ref.get('container-title', []), list) else ref.get('container-title')
                                ))
                            except Exception as e:
                                logger.warning(f"Error parsing individual reference: {str(e)}")
                                print(colored(f"⚠️ Error parsing reference: {str(e)}", "yellow"))
                                continue
                        
                        print(colored(f"✓ Extracted {len(metadata.references)} references with Anystyle", "green"))
                        
                        # Extract citations and link them to references
                        metadata.citations = []
                        citation_patterns = [
                            r'\[([\d,\s-]+)\]',  # [1] or [1,2] or [1-3]
                            r'\(([^)]+?(?:19|20)\d{2}[^)]*)\)',  # (Author, 2023) or (Author et al., 2023)
                            r'(?:cf\.|see|in)\s+([A-Z][a-zA-Z]+(?:\s+et\s+al\.?)?,\s+(?:19|20)\d{2})',  # cf. Author et al., 2023
                        ]
                        
                        for i, line in enumerate(lines):
                            for pattern in citation_patterns:
                                for match in re.finditer(pattern, line):
                                    citation_text = match.group(0)
                                    ref_key = match.group(1)
                                    
                                    # Get context (surrounding text)
                                    start = max(0, i-1)
                                    end = min(len(lines), i+2)
                                    context = ' '.join(lines[start:end])
                                    
                                    # Try to find matching references
                                    matching_refs = []
                                    if '[' in citation_text:  # Numeric citation
                                        try:
                                            ref_nums = []
                                            for part in ref_key.split(','):
                                                part = part.strip()
                                                if '-' in part:
                                                    start_num, end_num = map(int, part.split('-'))
                                                    ref_nums.extend(range(start_num, end_num + 1))
                                                else:
                                                    ref_nums.append(int(part))
                                            
                                            # Add each referenced paper
                                            for num in ref_nums:
                                                if 0 < num <= len(metadata.references):
                                                    matching_refs.append(metadata.references[num - 1])
                                        except (ValueError, IndexError) as e:
                                            logger.warning(f"Error parsing numeric citation {citation_text}: {str(e)}")
                                    else:  # Author-year citation
                                        # Split on 'and' or ';' for multiple author-year citations
                                        for author_year in re.split(r'\s+(?:and|;)\s+', ref_key):
                                            year_match = re.search(r'(?:19|20)\d{2}', author_year)
                                            if year_match:
                                                year = int(year_match.group())
                                                author_match = re.search(r'([A-Z][a-zA-Z]+)', author_year)
                                                if author_match:
                                                    author = author_match.group(1)
                                                    # Find matching reference
                                                    for ref in metadata.references:
                                                        if (ref.year == year and 
                                                            ref.authors and 
                                                            any(author.lower() in a.last_name.lower() for a in ref.authors)):
                                                            matching_refs.append(ref)
                                                            break
                                    
                                    # Create citation with all matching references
                                    metadata.citations.append(Citation(
                                        text=citation_text,
                                        references=matching_refs,  # Now a list of references
                                        context=context
                                    ))
                        
                        print(colored(f"✓ Extracted {len(metadata.citations)} citations", "green"))
                        
                except subprocess.CalledProcessError as e:
                    logger.error(f"Anystyle command failed: {e.stderr}")
                    print(colored(f"⚠️ Anystyle extraction failed: {e.stderr}", "yellow"))
                    
                finally:
                    # Clean up temp file
                    os.unlink(temp_path)
                    
            except Exception as e:
                logger.error(f"Reference extraction failed: {str(e)}")
                print(colored(f"⚠️ Reference extraction failed: {str(e)}", "yellow"))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
            print(colored(f"⚠️ Metadata extraction failed: {str(e)}", "yellow"))
            return AcademicMetadata(doc_id=doc_id) 