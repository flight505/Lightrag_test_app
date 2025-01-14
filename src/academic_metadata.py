"""Academic metadata models."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from termcolor import colored

from .base_metadata import Author, Reference
from .equation_metadata import Equation

class Citation(BaseModel):
    """Represents a citation within the text."""
    text: str = Field(description="The citation text")
    references: List[Reference] = Field(default_factory=list, description="The references this citation points to")
    context: str = Field(default="", description="The surrounding text context of the citation")

    model_config = {
        "arbitrary_types_allowed": True
    }

class AcademicMetadata(BaseModel):
    """Academic metadata for a document."""
    doc_id: str = Field(default="", description="Document identifier")
    title: str = Field(default="", description="Document title")
    authors: List[Author] = Field(default_factory=list, description="List of authors")
    abstract: str = Field(default="", description="Document abstract")
    references: List[Reference] = Field(default_factory=list, description="List of references")
    citations: List[Citation] = Field(default_factory=list, description="List of citations")
    equations: List[Equation] = Field(default_factory=list, description="List of equations")
    year: Optional[int] = Field(default=None, description="Publication year")
    identifier: Optional[str] = Field(default=None, description="DOI or arXiv identifier")
    identifier_type: Optional[str] = Field(default=None, description="Type of identifier (doi/arxiv)")
    journal: Optional[str] = Field(default=None, description="Journal name")
    source: Optional[str] = Field(default=None, description="Source of metadata (arxiv/crossref/text)")

    model_config = {
        "arbitrary_types_allowed": True
    }