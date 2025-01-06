import logging
import os
import re
from typing import Dict, List, Optional, Any
import pandas as pd
from termcolor import colored
from src.academic_metadata import AcademicMetadata, Reference

# Configure logging
logging.basicConfig(
    filename="lightrag.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class AcademicResponseProcessor:
    """Enhanced processor for academic responses with reference management"""

    def __init__(self):
        """Initialize the academic response processor"""
        self.source_cache = {}
        self.reference_cache = {}
        
    def _add_citations(self, text: str, references: List[Reference]) -> str:
        """Add academic citations to text with proper reference linking"""
        try:
            # Create citation key map
            citation_map = {ref.citation_key: ref for ref in references if ref.citation_key}
            
            def replace_citation(match):
                cite_text = match.group(1)
                # Try to find matching reference
                for key, ref in citation_map.items():
                    if key in cite_text or (ref.authors and ref.year and 
                        any(author.last_name in cite_text for author in ref.authors)):
                        # Format as (Author et al., YEAR) if multiple authors
                        if len(ref.authors) > 1:
                            return f"({ref.authors[0].last_name} et al., {ref.year})"
                        # Format as (Author, YEAR) if single author
                        elif ref.authors:
                            return f"({ref.authors[0].last_name}, {ref.year})"
                return match.group(0)
            
            # Replace citations
            text = re.sub(r'\[([^\]]+)\]', replace_citation, text)
            text = re.sub(r'\(([^)]+?)\s*\d{4}\)', replace_citation, text)
            
            return text
            
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

    def _format_references(self, references: List[Reference]) -> str:
        """Format academic references"""
        try:
            if not references:
                return ""
                
            formatted_refs = ["## References"]
            
            # Sort references by first author's last name and year
            sorted_refs = sorted(
                references,
                key=lambda r: (
                    r.authors[0].last_name if r.authors else "",
                    r.year if r.year else 0
                )
            )
            
            for ref in sorted_refs:
                # Format authors
                if ref.authors:
                    if len(ref.authors) > 1:
                        authors = f"{ref.authors[0].last_name} et al."
                    else:
                        authors = ref.authors[0].last_name
                else:
                    authors = "Unknown"
                
                # Format year
                year = f"({ref.year})" if ref.year else ""
                
                # Format title and venue
                title = f"*{ref.title}*" if ref.title else ""
                venue = f". {ref.venue}" if ref.venue else ""
                
                # Format DOI
                doi = f". DOI: {ref.doi}" if ref.doi else ""
                
                # Combine all parts
                formatted_ref = f"- {authors} {year}. {title}{venue}{doi}"
                formatted_refs.append(formatted_ref)
            
            return "\n".join(formatted_refs)
            
        except Exception as e:
            logger.error(f"Error formatting references: {str(e)}")
            return ""

    def process_response(self, response: str, metadata: Optional[AcademicMetadata] = None) -> str:
        """Process the response to enhance academic formatting"""
        try:
            if not response:
                return ""
            
            # Process the response string
            formatted_response = response
            
            # Add academic formatting
            if metadata and metadata.references:
                formatted_response = self._add_citations(formatted_response, metadata.references)
            formatted_response = self._format_equations(formatted_response)
            
            # Add formatted references if available
            if metadata and metadata.references:
                ref_section = self._format_references(metadata.references)
                if ref_section:
                    formatted_response += f"\n\n{ref_section}"
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error processing academic response: {str(e)}")
            return response

    def format_academic_response(
        self, 
        query: str, 
        result: Dict[str, Any],
        metadata: Optional[AcademicMetadata] = None,
        include_references: bool = True
    ) -> str:
        """Format response with academic styling and references"""
        try:
            response = result.get("response", "")
            mode = result.get("mode", "Unknown")
            
            # Format the response with metadata
            formatted_response = self.process_response(response, metadata)
            
            # Build the complete response
            complete_response = f"""
### Query
{query}

### Response
{formatted_response}

### Search Mode
{mode}
"""
            return complete_response.strip()
            
        except Exception as e:
            logger.error(f"Error formatting academic response: {str(e)}")
            raise

    def save_academic_response(
        self,
        query: str,
        result: Dict,
        metadata: Optional[AcademicMetadata],
        output_dir: str,
        filename: Optional[str] = None
    ) -> None:
        """Save academic response with metadata"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            if not filename:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                filename = f"academic_response_{timestamp}.txt"
            
            formatted_response = self.format_academic_response(
                query=query,
                result=result,
                metadata=metadata
            )
            
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_response)
                
            print(colored(f"Academic response saved to {output_path}", "green"))
            
        except Exception as e:
            error_msg = f"Error saving academic response: {str(e)}"
            logger.error(error_msg)
            raise 