from typing import Dict, Any, Optional, List
from termcolor import colored
import subprocess
import re
import tempfile
import json
import os
from .academic_metadata import Reference, Author, AcademicMetadata
from .equation_metadata import EquationExtractor
from pathlib import Path
import shutil

class MetadataExtractor:
    """Extracts metadata from academic documents"""
    
    def __init__(self, debug: bool = True):
        """Initialize metadata extractor and check Anystyle availability"""
        self.anystyle_available = False
        self.debug = debug
        self.equation_extractor = EquationExtractor(debug=debug)
        try:
            result = subprocess.run(['anystyle', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(colored(f"✓ Found Anystyle: {result.stdout.strip()}", "green"))
                self.anystyle_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(colored("⚠️ Anystyle not found. Please install it with: gem install anystyle-cli", "yellow"))
    
    def _parse_authors(self, author_data: List[Dict]) -> List[Author]:
        """Parse author information from Anystyle output"""
        authors = []
        try:
            for author in author_data:
                # Extract author parts
                given = author.get('given', '')
                family = author.get('family', '')
                
                # Skip if no name parts found
                if not given and not family:
                    continue
                    
                # Create full name
                full_name = f"{given} {family}".strip()
                
                # Create Author object
                author_obj = Author(
                    full_name=full_name,
                    first_name=given,
                    last_name=family
                )
                authors.append(author_obj)
                
        except (KeyError, TypeError, ValueError) as e:
            print(colored(f"⚠️ Error parsing author data: {str(e)}", "yellow"))
            
        return authors

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from text using common patterns."""
        # Look for title patterns
        title_patterns = [
            r'(?i)title[:\s]+([^\n]+)',  # Basic title pattern
            r'(?m)^#\s+(.+)$',  # Markdown title
            r'(?m)^(.+)\n={3,}$',  # Underlined title
            r'\\title{([^}]+)}',  # LaTeX title
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                if len(title) > 10:  # Basic validation
                    return title
        
        # Fallback: try first non-empty line
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and not line.startswith('#') and not line.lower().startswith('abstract'):
                return line
        
        return None

    def extract_metadata(self, text: str, doc_id: str, existing_metadata: Optional[Dict[str, Any]] = None) -> Optional[AcademicMetadata]:
        """Extract metadata from text, optionally using existing metadata"""
        try:
            # Initialize metadata object
            metadata = AcademicMetadata(doc_id=doc_id)
            
            # If we have existing metadata, use it
            if existing_metadata:
                metadata.title = existing_metadata.get('title', '')
                metadata.abstract = existing_metadata.get('abstract', '')
                metadata.identifier = existing_metadata.get('identifier', '')
                metadata.identifier_type = existing_metadata.get('identifier_type', '')
                metadata.year = existing_metadata.get('year')
                metadata.journal = existing_metadata.get('journal', '')
                metadata.source = existing_metadata.get('source', '')
                metadata.validation_info = existing_metadata.get('validation_info', {})
                metadata.extraction_method = existing_metadata.get('extraction_method', '')
                
                # Convert author dictionaries to Author objects
                if 'authors' in existing_metadata:
                    metadata.authors = []
                    for author_data in existing_metadata['authors']:
                        if isinstance(author_data, dict):
                            given = author_data.get('given', '')
                            family = author_data.get('family', '')
                            full_name = author_data.get('full_name', f"{given} {family}".strip())
                            metadata.authors.append(Author(full_name=full_name))
            
            # Extract references using Anystyle
            if self.anystyle_available:
                references = self._extract_references_with_anystyle(text)
                if references:
                    metadata.references = references
                    print(colored(f"✓ Found {len(references)} references", "green"))
                else:
                    print(colored("⚠️ No references parsed", "yellow"))
            
            # Extract equations
            equations = self.equation_extractor.extract_equations(text)
            if equations:
                metadata.equations = equations
                print(colored(f"✓ Found {len(equations)} equations", "green"))
            else:
                print(colored("⚠️ No equations found", "yellow"))
            
            return metadata
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting metadata: {str(e)}", "yellow"))
            return None

    def _extract_references_with_anystyle(self, text: str) -> List[Reference]:
        """Extract references from text using Anystyle CLI."""
        if not self.anystyle_available:
            print(colored("⚠️ Anystyle not available, skipping reference extraction", "yellow"))
            return []

        # Try to find references section using different patterns
        patterns = [
            r'#\s*\*?\*?References\*?\*?\s*\n(.*?)(?=\n#|$)',  # Single # with optional **
            r'#{2}\s*\*?\*?References\*?\*?\s*\n(.*?)(?=\n#{2}|$)',  # Double ## with optional **
            r'References\s*\n(.*?)(?=\n\n|$)',     # Plain text style
            r'\[\d+\].*?(?=\[\d+\]|\Z)',          # Numbered references
            r'\[\d+\].*?(?=\n\n|\Z)'              # Single reference
        ]
        
        references_text = ""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            if matches:
                references_text = '\n'.join(matches)
                if self.debug:
                    print(colored(f"✓ Found references section with pattern: {pattern}", "green"))
                break
        
        if not references_text:
            print(colored("⚠️ No references section found in text", "yellow"))
            return []

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_in:
                # Clean up reference text - remove markdown formatting
                references_text = re.sub(r'\*\*(.*?)\*\*', r'\1', references_text)  # Remove bold
                references_text = re.sub(r'\*(.*?)\*', r'\1', references_text)      # Remove italics
                temp_in.write(references_text)
                temp_in.flush()
                
                # Run Anystyle parse command and capture output directly
                parse_cmd = ['anystyle', '--format', 'json', 'parse', temp_in.name]
                if self.debug:
                    print(colored(f"Running command: {' '.join(parse_cmd)}", "blue"))
                result = subprocess.run(parse_cmd, capture_output=True, text=True, check=True)
                
                try:
                    references_data = json.loads(result.stdout)
                    references = []
                    
                    for ref in references_data:
                        try:
                            # Extract year from date if present
                            year = None
                            if 'date' in ref:
                                year_match = re.search(r'\b\d{4}\b', ref['date'][0])
                                if year_match:
                                    year = int(year_match.group())
                            
                            # Create Reference object
                            reference = Reference(
                                raw_text=ref.get('original', ''),
                                title=ref.get('title', [''])[0] if ref.get('title') else '',
                                authors=[Author(full_name=author) for author in ref.get('author', [])],
                                year=year,
                                doi=ref.get('doi', [''])[0] if ref.get('doi') else None,
                                venue=ref.get('journal', [''])[0] if ref.get('journal') else None
                            )
                            references.append(reference)
                        except (KeyError, TypeError, ValueError) as e:
                            print(colored(f"⚠️ Error parsing reference: {e}", "yellow"))
                            continue
                    
                    print(colored(f"✓ Successfully parsed {len(references)} references", "green"))
                    return references
                    
                except json.JSONDecodeError as e:
                    print(colored(f"⚠️ Error decoding JSON from Anystyle output: {e}", "red"))
                    return []
                    
        except subprocess.CalledProcessError as e:
            print(colored(f"⚠️ Anystyle parse failed with code {e.returncode}", "red"))
            if e.stderr:
                print(colored(f"Error output: {e.stderr}", "red"))
            return []
        except Exception as e:
            print(colored(f"⚠️ Error during reference extraction: {e}", "red"))
            return []
        finally:
            try:
                os.unlink(temp_in.name)
            except Exception as e:
                print(colored(f"⚠️⚠️⚠️ Error removing temporary file: {e}", "yellow")) 