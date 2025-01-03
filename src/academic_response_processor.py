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

    def _add_citations(self, text: str) -> str:
        """Add academic citations to text"""
        try:
            # Extract potential citations and add proper formatting
            citation_pattern = r'\[([^\]]+)\]'
            return re.sub(citation_pattern, r'(\1)', text)
        except Exception as e:
            logger.error(f"Error adding citations: {str(e)}")
            return text

    def _format_equations(self, text: str) -> str:
        """Format mathematical equations in text"""
        try:
            # Ensure equations are properly formatted with newlines
            text = re.sub(r'(?<!\n)\$\$', '\n$$', text)
            text = re.sub(r'\$\$(?!\n)', '$$\n', text)
            return text
        except Exception as e:
            logger.error(f"Error formatting equations: {str(e)}")
            return text

    def _format_references(self, text: str) -> str:
        """Format academic references in text"""
        try:
            # Look for reference section and format it
            ref_section_pattern = r'(References:|Bibliography:|Sources:)(.*?)(?=\n\n|$)'
            
            def format_ref_section(match):
                header = match.group(1)
                content = match.group(2)
                # Format each reference on a new line with bullet points
                formatted_refs = '\n'.join(f'- {ref.strip()}' 
                                         for ref in content.split('\n') 
                                         if ref.strip())
                return f'{header}\n{formatted_refs}'
            
            return re.sub(ref_section_pattern, format_ref_section, text, flags=re.DOTALL)
        except Exception as e:
            logger.error(f"Error formatting references: {str(e)}")
            return text

    def process_response(self, response: str) -> str:
        """Process the response to enhance academic formatting"""
        try:
            if not response:
                return ""
            
            # Process the response string directly
            formatted_response = response
            
            # Add academic formatting
            formatted_response = self._add_citations(formatted_response)
            formatted_response = self._format_equations(formatted_response)
            formatted_response = self._format_references(formatted_response)
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error processing academic response: {str(e)}")
            return response  # Return original response if processing fails

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