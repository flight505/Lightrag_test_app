from abc import ABC, abstractmethod
from typing import List
from termcolor import colored
from .academic_metadata import Reference, Author, CitationStyle

class CitationFormatter(ABC):
    """Abstract base class for citation formatters"""
    
    @abstractmethod
    def format_citation(self, reference: Reference) -> str:
        """Format a single citation"""
        pass
    
    @abstractmethod
    def format_bibliography(self, references: List[Reference]) -> str:
        """Format a bibliography"""
        pass
    
    def _format_authors(self, authors: List[Author], use_full_names: bool = True) -> str:
        """Format author names - can be overridden by subclasses"""
        if not authors:
            return "Unknown Author"
        
        if len(authors) == 1:
            return self._format_author(authors[0], use_full_names)
        elif len(authors) == 2:
            return f"{self._format_author(authors[0], use_full_names)} and {self._format_author(authors[1], use_full_names)}"
        else:
            return f"{self._format_author(authors[0], use_full_names)} et al."
    
    def _format_author(self, author: Author, use_full_names: bool = True) -> str:
        """Format a single author name"""
        if not use_full_names:
            return author.last_name if author.last_name else author.full_name
            
        if author.last_name and author.first_name:
            return f"{author.last_name}, {author.first_name}"
        return author.full_name
    
    def _clean_title(self, title: str) -> str:
        """Clean and format title"""
        if not title:
            return "Untitled"
        return title.strip().rstrip('.')

class APAFormatter(CitationFormatter):
    """APA (7th edition) citation formatter"""
    
    def format_citation(self, reference: Reference) -> str:
        try:
            authors = self._format_authors(reference.authors, use_full_names=False)
            year = reference.year or "n.d."
            
            return f"({authors}, {year})"
            
        except Exception as e:
            print(colored(f"⚠️ Error formatting APA citation: {str(e)}", "yellow"))
            return f"({reference.raw_text})"
    
    def format_bibliography(self, references: List[Reference]) -> str:
        try:
            formatted = []
            for ref in sorted(references, key=lambda r: (
                r.authors[0].last_name if r.authors else "Unknown",
                r.year or "n.d."
            )):
                authors = self._format_authors(ref.authors)
                year = ref.year or "n.d."
                title = self._clean_title(ref.title)
                venue = ref.venue or "Unknown venue"
                
                entry = f"{authors} ({year}). {title}. {venue}."
                if ref.doi:
                    entry += f" https://doi.org/{ref.doi}"
                
                formatted.append(entry)
            
            return "\n\n".join(formatted)
            
        except Exception as e:
            print(colored(f"⚠️ Error formatting APA bibliography: {str(e)}", "yellow"))
            return "\n\n".join(r.raw_text for r in references)

class MLAFormatter(CitationFormatter):
    """MLA (9th edition) citation formatter"""
    
    def format_citation(self, reference: Reference) -> str:
        try:
            authors = self._format_authors(reference.authors, use_full_names=False)
            page = "n.p."  # Page numbers would be added in context
            
            return f"({authors} {page})"
            
        except Exception as e:
            print(colored(f"⚠️ Error formatting MLA citation: {str(e)}", "yellow"))
            return f"({reference.raw_text})"
    
    def format_bibliography(self, references: List[Reference]) -> str:
        try:
            formatted = []
            for ref in sorted(references, key=lambda r: (
                r.authors[0].last_name if r.authors else "Unknown"
            )):
                authors = self._format_authors(ref.authors)
                title = f'"{self._clean_title(ref.title)}"'
                venue = ref.venue or "Unknown venue"
                year = ref.year or "n.d."
                
                entry = f"{authors}. {title}. {venue}, {year}"
                if ref.doi:
                    entry += f", https://doi.org/{ref.doi}"
                entry += "."
                
                formatted.append(entry)
            
            return "\n\n".join(formatted)
            
        except Exception as e:
            print(colored(f"⚠️ Error formatting MLA bibliography: {str(e)}", "yellow"))
            return "\n\n".join(r.raw_text for r in references)

class ChicagoFormatter(CitationFormatter):
    """Chicago (17th edition) citation formatter"""
    
    def format_citation(self, reference: Reference) -> str:
        try:
            authors = self._format_authors(reference.authors, use_full_names=False)
            year = reference.year or "n.d."
            
            return f"({authors} {year})"
            
        except Exception as e:
            print(colored(f"⚠️ Error formatting Chicago citation: {str(e)}", "yellow"))
            return f"({reference.raw_text})"
    
    def format_bibliography(self, references: List[Reference]) -> str:
        try:
            formatted = []
            for ref in sorted(references, key=lambda r: (
                r.authors[0].last_name if r.authors else "Unknown"
            )):
                authors = self._format_authors(ref.authors)
                year = ref.year or "n.d."
                title = f'"{self._clean_title(ref.title)}"'
                venue = ref.venue or "Unknown venue"
                
                entry = f"{authors}. {year}. {title}. {venue}"
                if ref.doi:
                    entry += f". https://doi.org/{ref.doi}"
                entry += "."
                
                formatted.append(entry)
            
            return "\n\n".join(formatted)
            
        except Exception as e:
            print(colored(f"⚠️ Error formatting Chicago bibliography: {str(e)}", "yellow"))
            return "\n\n".join(r.raw_text for r in references)

class CitationFormatterFactory:
    """Factory for creating citation formatters"""
    
    _formatters = {
        CitationStyle.APA: APAFormatter,
        CitationStyle.MLA: MLAFormatter,
        CitationStyle.CHICAGO: ChicagoFormatter
    }
    
    @classmethod
    def create_formatter(cls, style: CitationStyle) -> CitationFormatter:
        """Create a citation formatter for the specified style"""
        formatter_class = cls._formatters.get(style)
        if not formatter_class:
            print(colored(f"⚠️ Unknown citation style: {style}, falling back to APA", "yellow"))
            formatter_class = APAFormatter
        
        return formatter_class() 