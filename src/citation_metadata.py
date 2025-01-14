"""Citation metadata and processing classes."""
import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, model_validator
from termcolor import colored

from .base_metadata import Author, Reference
from .academic_metadata import Citation


class CitationLocation(BaseModel):
    """Location of a citation in the document."""
    paragraph: int
    offset: int

    model_config = {
        "arbitrary_types_allowed": True
    }

class CitationLink(BaseModel):
    """Represents a link between an inline citation and its reference."""
    citation_text: str
    reference: Reference
    context: str
    location: CitationLocation
    
    def to_citation(self) -> Citation:
        """Convert CitationLink to Citation."""
        return Citation(
            text=self.citation_text,
            references=[self.reference],
            context=self.context
        )

    model_config = {
        "arbitrary_types_allowed": True
    }

class CitationProcessor:
    """Processes inline citations and links them to references."""
    
    CITATION_PATTERNS = {
        'cross_ref': [
            r'(?:^|\s|[^\w.])cf\.\s+([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)'  # cf. Smith et al. (2023)
        ],
        'author_year': [
            r'(?:^|\s|[^\w.])(?<!cf\.\s)([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)(?!\s*\))',  # Smith et al. (2023)
            r'(?:^|\s|[^\w.])(?<!cf\.\s)([A-Z][a-z]+)\s+(?:and|&)\s+[A-Z][a-z]+\s*\((\d{4})\)',  # Smith and Jones (2023)
            r'(?:^|\s|[^\w.])(?<!cf\.\s)[A-Z][a-z]+\s+(?:and|&)\s+([A-Z][a-z]+)\s*\((\d{4})\)'   # Smith and Jones (2023)
        ],
        'numeric': [
            r'\[(\d+(?:\s*,\s*\d+)*)\]',  # [1] or [1,2,3]
            r'\[(\d+\s*-\s*\d+)\]'        # [1-3]
        ]
    }
    
    def __init__(self, references: List[Reference]):
        self.references = references
        self.citation_links: List[CitationLink] = []
    
    def _get_context(self, text: str, match: re.Match, window: int = 100) -> str:
        """Extract context around a citation match."""
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        return text[start:end].strip()
    
    def _get_location(self, text: str, match: re.Match) -> CitationLocation:
        """Get the location of a citation in the document."""
        # Count newlines up to match start to determine paragraph
        text_before = text[:match.start()]
        paragraph = text_before.count('\n\n')
        # Get offset within paragraph
        last_para_start = text_before.rfind('\n\n')
        offset = match.start() - (last_para_start + 2 if last_para_start != -1 else 0)
        return CitationLocation(paragraph=paragraph, offset=offset)
    
    def process_citations(self, text: str) -> List[CitationLink]:
        """Process all citations in text and link them to references."""
        citations = []
        
        # Process in strict order: cross_ref -> numeric -> author_year
        for style in ['cross_ref', 'numeric', 'author_year']:
            for pattern in self.CITATION_PATTERNS[style]:
                for match in re.finditer(pattern, text):
                    citation_text = match.group(0).strip()
                    if style == 'numeric':
                        # For numeric citations, try to find all referenced indices
                        numbers = match.group(1)
                        try:
                            if '-' in numbers:
                                start, end = map(int, numbers.split('-'))
                                if start > len(self.references) or end > len(self.references):
                                    continue
                                indices = range(start-1, end)
                            else:
                                indices = [int(n.strip())-1 for n in numbers.split(',')]
                                if any(idx >= len(self.references) for idx in indices):
                                    continue
                            
                            # Get all valid references
                            valid_refs = []
                            for idx in indices:
                                if 0 <= idx < len(self.references):
                                    valid_refs.append(self.references[idx])
                            
                            # Create a single citation with all valid references
                            if valid_refs:
                                try:
                                    citation = CitationLink(
                                        citation_text=citation_text,
                                        reference=valid_refs[0],  # Use first ref as primary
                                        context=self._get_context(text, match),
                                        location=self._get_location(text, match)
                                    )
                                    citations.append(citation)
                                except Exception as e:
                                    print(colored(f"Error creating citation: {e}", "red"))
                        except (ValueError, IndexError):
                            continue
                    else:
                        # For author-year citations, find the matching reference
                        if reference := self._find_matching_reference(match, style):
                            try:
                                citation = CitationLink(
                                    citation_text=citation_text,
                                    reference=reference,
                                    context=self._get_context(text, match),
                                    location=self._get_location(text, match)
                                )
                                citations.append(citation)
                            except Exception as e:
                                print(colored(f"Error creating citation: {e}", "red"))
        
        self.citation_links = citations
        return citations
    
    def _find_matching_reference(self, match: re.Match, style: str) -> Optional[Reference]:
        """Find the reference that matches the citation."""
        if style == 'numeric':
            numbers = match.group(1)
            try:
                if '-' in numbers:
                    start, end = map(int, numbers.split('-'))
                    if start > len(self.references) or end > len(self.references):
                        return None
                    indices = range(start-1, end)
                else:
                    indices = [int(n.strip())-1 for n in numbers.split(',')]
                    if any(idx >= len(self.references) for idx in indices):
                        return None
                
                # Return first valid reference
                for idx in indices:
                    if 0 <= idx < len(self.references):
                        return self.references[idx]
            except (ValueError, IndexError):
                return None
        
        elif style in ['author_year', 'cross_ref']:
            author = match.group(1)
            year = int(match.group(2))
            
            # Clean up author name
            if style == 'cross_ref':
                author = author.lower().replace('cf.', '').strip()
            author = author.lower().replace('et al.', '').strip()
            
            # Find matching reference
            for ref in self.references:
                if ref.year == year and ref.authors:
                    for ref_author in ref.authors:
                        if ref_author.last_name and ref_author.last_name.lower().startswith(author.lower()):
                            return ref
        
        return None
    
    def get_citation_graph(self) -> Dict[str, List[str]]:
        """Get citation graph as adjacency list."""
        graph = {}
        for citation in self.citation_links:
            if citation.reference.title not in graph:
                graph[citation.reference.title] = []
            if citation.context not in graph[citation.reference.title]:
                graph[citation.reference.title].append(citation.context)
        return graph
    
    def validate_citations(self) -> List[Dict[str, Any]]:
        """Validate all citations and return issues."""
        issues = []
        for citation in self.citation_links:
            if not citation.reference:
                issues.append({
                    'type': 'unresolved_citation',
                    'citation': citation.citation_text,
                    'context': citation.context,
                    'location': citation.location.dict()
                })
        return issues 