from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
import json
import subprocess
import tempfile
import networkx as nx
import matplotlib.pyplot as plt
from termcolor import colored
import re

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
    """Represents an academic reference with structured information."""
    raw_text: str
    title: Optional[str] = None
    authors: List[Author] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    citation_key: Optional[str] = None
    cited_by: Set[str] = field(default_factory=set)
    cites: Set[str] = field(default_factory=set)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Reference':
        data = data.copy()
        if 'authors' in data:
            data['authors'] = [Author.from_dict(a) for a in data['authors']]
        if 'cited_by' in data:
            data['cited_by'] = set(data['cited_by'])
        if 'cites' in data:
            data['cites'] = set(data['cites'])
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'raw_text': self.raw_text,
            'title': self.title,
            'authors': [a.to_dict() for a in self.authors],
            'year': self.year,
            'doi': self.doi,
            'venue': self.venue,
            'citation_key': self.citation_key,
            'cited_by': list(self.cited_by),
            'cites': list(self.cites)
        }
    
    def validate(self, validator: 'ReferenceValidator') -> 'ValidationResult':
        return validator.validate(self)

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
    """Container for all academic metadata of a document."""
    title: str
    authors: List[Author]
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AcademicMetadata':
        data = data.copy()
        if 'authors' in data:
            data['authors'] = [Author.from_dict(a) for a in data['authors']]
        if 'references' in data:
            data['references'] = [Reference.from_dict(r) for r in data['references']]
        if 'equations' in data:
            data['equations'] = [Equation.from_dict(e) for e in data['equations']]
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'authors': [a.to_dict() for a in self.authors],
            'abstract': self.abstract,
            'keywords': self.keywords,
            'references': [r.to_dict() for r in self.references],
            'equations': [e.to_dict() for e in self.equations]
        }
    
    def save(self, output_dir: Path) -> None:
        """Save metadata to JSON file."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Sanitize filename
            safe_title = re.sub(r'[^\w\-_\. ]', '_', self.title)
            safe_title = safe_title[:100]  # Limit length
            output_path = output_dir / f"{safe_title}_metadata.json"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)
            print(colored(f"✓ Saved metadata to {output_path}", "green"))
            
        except Exception as e:
            print(colored(f"❌ Failed to save metadata: {e}", "red"))
            raise

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

class MetadataExtractor:
    """Extracts academic metadata from document text."""
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
    
    def extract_metadata(self, text: str, doc_id: str) -> AcademicMetadata:
        """Extract academic metadata from document text."""
        # Extract title (first non-empty line)
        lines = text.split('\n')
        title = next((line.strip() for line in lines if line.strip()), "Untitled Document")
        
        # Extract authors (look for common patterns)
        author_line = next((line.strip() for line in lines[1:] 
                          if "author" in line.lower() or "@" in line), "")
        authors = self._parse_authors(author_line.split(','))
        
        # Extract abstract
        abstract_start = text.lower().find('abstract')
        abstract = ""
        if abstract_start != -1:
            abstract_end = text.lower().find('introduction', abstract_start)
            if abstract_end != -1:
                abstract = text[abstract_start:abstract_end].strip()
        
        # Extract references
        references_start = text.lower().find('references')
        if references_start != -1:
            references_text = text[references_start:].split('\n')
            references = self._parse_references(references_text)
        else:
            references = []
        
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
        """Extract equations from text."""
        equations = []
        eq_id = 1
        
        # Simple equation extraction (can be enhanced)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if '$' in line or '\\[' in line:
                # Get context (surrounding lines)
                start = max(0, i-2)
                end = min(len(lines), i+3)
                context = '\n'.join(lines[start:end])
                
                # Determine equation type
                if '\\[' in line or '\\begin{equation}' in line:
                    eq_type = EquationType.DISPLAY
                else:
                    eq_type = EquationType.INLINE
                
                equations.append(Equation(
                    raw_text=line,
                    equation_id=f"eq{eq_id}",
                    context=context,
                    equation_type=eq_type,
                    symbols=set()  # Symbol extraction can be added
                ))
                eq_id += 1
        
        return equations 
    
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