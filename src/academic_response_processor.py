import logging
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pandas as pd
from termcolor import colored

# Configure logging
logging.basicConfig(
    filename="lightrag.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@dataclass
class AcademicReference:
    """Data class for academic references"""
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    source_file: str = ""
    citation_key: Optional[str] = None
    reference_text: Optional[str] = None

class AcademicResponseProcessor:
    """Enhanced processor for academic responses with reference management"""

    def __init__(self):
        """Initialize the academic response processor"""
        self.source_cache = {}
        self.reference_cache = {}
        
    def extract_references_from_text(self, text: str) -> List[AcademicReference]:
        """Extract academic references from text content
        
        Looks for common citation patterns and reference list formats
        """
        try:
            references = []
            
            # Look for reference section
            ref_section_pattern = r"(?:References|Bibliography|Works Cited)[\s\n]+((?:(?:[^\n]+\n)+))"
            ref_match = re.search(ref_section_pattern, text, re.IGNORECASE)
            
            if ref_match:
                ref_text = ref_match.group(1)
                # Split into individual references
                ref_entries = re.split(r"\n(?=\d+\.|\[|\()", ref_text)
                
                for entry in ref_entries:
                    if not entry.strip():
                        continue
                        
                    # Extract basic reference info
                    # This is a simple example - expand based on common formats
                    author_year = re.search(r"([^(]+)\((\d{4})\)", entry)
                    if author_year:
                        authors = [a.strip() for a in author_year.group(1).split(",")]
                        year = int(author_year.group(2))
                        
                        ref = AcademicReference(
                            title=entry.strip(),
                            authors=authors,
                            year=year,
                            reference_text=entry.strip()
                        )
                        references.append(ref)
            
            return references

        except Exception as e:
            logger.error(f"Error extracting references: {str(e)}")
            return []

    def process_response(self, result: Dict[str, Any]) -> Tuple[str, List[AcademicReference]]:
        """Process the LightRAG response and extract academic components
        
        Args:
            result: Raw response dictionary from LightRAG
            
        Returns:
            Tuple containing:
            - Processed response text
            - List of academic references
        """
        try:
            response = result.get("response", "")
            sources = result.get("sources", [])
            
            # Extract references from response text
            references = self.extract_references_from_text(response)
            
            # Add source documents as references
            for source in sources:
                if isinstance(source, str) and source not in self.source_cache:
                    ref = AcademicReference(
                        title=source,
                        source_file=source
                    )
                    references.append(ref)
                    self.source_cache[source] = ref
                    
            return response, references

        except Exception as e:
            error_msg = f"Error processing academic response: {str(e)}"
            logger.error(error_msg)
            raise

    def format_academic_response(
        self, 
        query: str, 
        result: Dict[str, Any],
        include_references: bool = True
    ) -> str:
        """Format response with academic styling and references
        
        Args:
            query: Original query
            result: Raw response from LightRAG
            include_references: Whether to include reference list
        """
        try:
            response, references = self.process_response(result)
            mode = result.get("mode", "Unknown")
            
            # Format equations
            if '$$' in response:
                response = response.replace('$$', '\n$$\n')
            
            # Format in-text citations
            for ref in references:
                if ref.authors and ref.year:
                    citation = f"({ref.authors[0].split()[-1]}, {ref.year})"
                    # Add citation if not already present
                    if citation not in response:
                        response += f"\n\nSource: {citation}"
            
            formatted_response = f"""
### Query
{query}

### Response
{response}

### Search Mode
{mode}
"""
            
            if include_references and references:
                ref_list = "\n\n### References\n"
                for i, ref in enumerate(references, 1):
                    ref_text = ref.reference_text if ref.reference_text else f"{ref.title}"
                    ref_list += f"{i}. {ref_text}\n"
                formatted_response += ref_list
            
            return formatted_response

        except Exception as e:
            logger.error(f"Error formatting academic response: {str(e)}")
            raise

    def save_academic_response(
        self,
        query: str,
        result: Dict,
        output_dir: str,
        filename: Optional[str] = None
    ) -> None:
        """Save academic response with metadata
        
        Args:
            query: Original query
            result: Raw response from LightRAG
            output_dir: Output directory
            filename: Optional custom filename
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            if not filename:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                filename = f"academic_response_{timestamp}.txt"
            
            formatted_response = self.format_academic_response(query, result)
            
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_response)
                
            print(colored(f"Academic response saved to {output_path}", "green"))
            
        except Exception as e:
            error_msg = f"Error saving academic response: {str(e)}"
            logger.error(error_msg)
            raise 