"""Base metadata models using Pydantic for validation."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Author(BaseModel):
    """Represents an author of an academic document."""
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None
    
    @field_validator('full_name', 'last_name', mode='before')
    @classmethod
    def parse_name(cls, v):
        """Parse author name from various formats."""
        if isinstance(v, dict):
            if 'family' in v and 'given' in v:
                return f"{v['given']} {v['family']}"
            elif 'literal' in v:
                return v['literal']
            elif 'full_name' in v:
                return v['full_name']
        return v
    
    @model_validator(mode='after')
    def ensure_names(self) -> 'Author':
        """Ensure names are consistent."""
        if not self.full_name and self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"
        elif self.full_name and not (self.first_name or self.last_name):
            parts = self.full_name.split()
            if len(parts) > 1:
                self.first_name = ' '.join(parts[:-1])
                self.last_name = parts[-1]
            else:
                self.last_name = self.full_name
        return self

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        return {
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'affiliation': self.affiliation,
            'email': self.email,
            'orcid': self.orcid
        }

class Reference(BaseModel):
    """A reference to another academic work."""
    raw_text: str = Field(description="The raw text of the reference")
    title: Optional[str] = Field(default=None, description="The title of the referenced work")
    authors: List[Author] = Field(default_factory=list, description="The authors of the referenced work")
    year: Optional[int] = Field(default=None, description="The year of publication")
    doi: Optional[str] = Field(default=None, description="The DOI of the referenced work")
    venue: Optional[str] = Field(default=None, description="The venue (journal/conference) of the referenced work")

    model_config = {
        "arbitrary_types_allowed": True
    }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert Reference to dictionary for JSON serialization."""
        return {
            'raw_text': self.raw_text,
            'title': self.title,
            'authors': [author.model_dump() for author in self.authors],
            'year': self.year,
            'doi': self.doi,
            'venue': self.venue
        }

class AcademicMetadata(BaseModel):
    """Represents metadata for an academic document."""
    doc_id: str = Field(default="")
    title: str = Field(default="")
    authors: List[Author] = Field(default_factory=list)
    abstract: str = Field(default="")
    references: List[Reference] = Field(default_factory=list)
    identifier: str = Field(default="")
    identifier_type: str = Field(default="")
    year: Optional[int] = Field(default=None)
    journal: str = Field(default="")
    source: str = Field(default="")
    equations: List[str] = Field(default_factory=list)

    model_config = {
        "arbitrary_types_allowed": True
    }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert model to dictionary format."""
        data = super().model_dump(**kwargs)
        data["authors"] = [author.model_dump(**kwargs) for author in self.authors]
        data["references"] = [ref.model_dump(**kwargs) for ref in self.references]
        data["equations"] = [str(eq) for eq in self.equations]  # Convert equations to strings
        return data 