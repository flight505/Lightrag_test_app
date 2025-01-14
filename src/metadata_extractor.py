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
import requests

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

    def extract_metadata(self, text: str, doc_id: str, pdf_path: Optional[str] = None, existing_metadata: Dict = None) -> AcademicMetadata:
        """Extract academic metadata from text and PDF, reusing existing metadata if available"""
        try:
            # If we have existing metadata from arXiv or DOI, use it but add references
            if existing_metadata and existing_metadata.get('source') in ['arxiv', 'crossref']:
                print(colored(f"✓ Using existing {existing_metadata['source']} metadata", "green"))
                
                # Convert authors to proper Author objects
                authors = []
                for author_data in existing_metadata.get('authors', []):
                    if isinstance(author_data, dict):
                        given = author_data.get('given', '')
                        family = author_data.get('family', '')
                        full_name = f"{given} {family}".strip()
                        authors.append(Author(
                            full_name=full_name,
                            first_name=given,
                            last_name=family
                        ))
                    elif isinstance(author_data, Author):
                        authors.append(author_data)
                
                # Extract references using API data first, then fallback to text
                if self.anystyle_available:
                    print(colored("→ Extracting references...", "blue"))
                    references = self._extract_references_with_anystyle(text, existing_metadata)
                    if references:
                        print(colored(f"✓ Found {len(references)} references", "green"))
                        
                        # Extract equations
                        equations = self.equation_extractor.extract_equations(text)
                        if equations:
                            print(colored(f"✓ Found {len(equations)} equations", "green"))
                        else:
                            print(colored("⚠️ No equations found", "yellow"))
                            equations = []
                            
                        return AcademicMetadata(
                            doc_id=doc_id,
                            title=existing_metadata.get('title', ''),
                            authors=authors,
                            abstract=existing_metadata.get('abstract', ''),
                            references=references,
                            identifier=existing_metadata.get('identifier', ''),
                            identifier_type=existing_metadata.get('identifier_type', ''),
                            year=existing_metadata.get('year'),
                            journal=existing_metadata.get('journal', ''),
                            source=existing_metadata.get('source', ''),
                            equations=equations
                        )
                else:
                    print(colored("⚠️ Anystyle not available - skipping reference extraction", "yellow"))
                    
            # If no existing metadata or reference extraction failed, parse from text
            return self._parse_from_text(text)
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting metadata: {str(e)}", "yellow"))
            return None

    def _extract_references_with_anystyle(self, text: str, metadata: Optional[Dict] = None) -> List[Reference]:
        """Extract references from text using Anystyle CLI and API data if available."""
        references = []

        # Try API-based references first if metadata is available
        if metadata:
            if metadata.get('source') == 'arxiv':
                try:
                    arxiv_id = metadata.get('identifier')
                    if arxiv_id:
                        import arxiv
                        search = arxiv.Search(id_list=[arxiv_id])
                        paper = next(search.results())
                        if hasattr(paper, 'references'):
                            for ref in paper.references:
                                try:
                                    references.append(Reference(
                                        raw_text=str(ref),
                                        title=ref.title if hasattr(ref, 'title') else None,
                                        authors=[Author(full_name=str(a)) for a in ref.authors] if hasattr(ref, 'authors') else [],
                                        year=ref.year if hasattr(ref, 'year') else None,
                                        doi=ref.doi if hasattr(ref, 'doi') else None,
                                        venue=ref.journal if hasattr(ref, 'journal') else None
                                    ))
                                except Exception as e:
                                    print(colored(f"⚠️ Error parsing arXiv reference: {e}", "yellow"))
                            if references:
                                print(colored(f"✓ Found {len(references)} references from arXiv API", "green"))
                                return references
                except Exception as e:
                    print(colored(f"⚠️ Error getting arXiv references: {e}", "yellow"))

            elif metadata.get('source') == 'crossref':
                try:
                    doi = metadata.get('identifier')
                    if doi:
                        response = requests.get(f"https://api.crossref.org/works/{doi}")
                        if response.status_code == 200:
                            data = response.json()['message']
                            if 'reference' in data:
                                for ref in data['reference']:
                                    try:
                                        year = None
                                        if 'year' in ref:
                                            year_match = re.search(r'\d{4}', str(ref['year']))
                                            if year_match:
                                                year = int(year_match.group())
                                        
                                        references.append(Reference(
                                            raw_text=ref.get('unstructured', ''),
                                            title=ref.get('article-title', ''),
                                            authors=[Author(full_name=ref.get('author', ''))],
                                            year=year,
                                            doi=ref.get('DOI'),
                                            venue=ref.get('journal-title')
                                        ))
                                    except Exception as e:
                                        print(colored(f"⚠️ Error parsing Crossref reference: {e}", "yellow"))
                                if references:
                                    print(colored(f"✓ Found {len(references)} references from Crossref API", "green"))
                                    return references
                except Exception as e:
                    print(colored(f"⚠️ Error getting Crossref references: {e}", "yellow"))

        # If no API references found, try text-based extraction
        if not references:
            # Try to find references section using different patterns
            patterns = [
                r'(?i)^#+\s*\**references\**\s*$\n(.*?)(?=^#+|\Z)',  # Markdown headers with optional asterisks
                r'(?i)^references$\n-+\n(.*?)(?=\n\n\w|\Z)',  # Underlined style
                r'(?i)\[\s*references\s*\]\n(.*?)(?=\n\[|\Z)',  # Bracketed style
                r'(?i)(?:bibliography|works cited|citations)\n(.*?)(?=\n\n\w|\Z)'  # Alternative headers
            ]
            
            references_text = ""
            for pattern in patterns:
                if self.debug:
                    print(colored(f"→ Trying pattern: {pattern}", "blue"))
                matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
                if matches:
                    references_text = '\n'.join(matches)
                    if self.debug:
                        print(colored(f"✓ Found references section with pattern: {pattern}", "green"))
                        line_count = len(references_text.split('\n'))
                        print(colored(f"→ Found {line_count} lines", "blue"))
                    break
            
            if not references_text:
                # Fallback: try to find numbered references directly
                numbered_pattern = r'(?m)^\s*(?:\[?\d+[\.\]]\s+|\d+\.\s+)(.*?)(?=^\s*(?:\[?\d+[\.\]]\s+|\d+\.\s+)|\Z)'
                matches = re.findall(numbered_pattern, text, re.DOTALL | re.MULTILINE)
                if matches:
                    references_text = '\n'.join(matches)
                    if self.debug:
                        print(colored("✓ Found references using numbered pattern fallback", "green"))
                        match_count = len(matches)
                        print(colored(f"→ Found {match_count} numbered references", "blue"))

            if not references_text:
                print(colored("⚠️ No references section found in text", "yellow"))
                return []

            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_in:
                    # Clean up reference text
                    references_text = re.sub(r'\*\*(.*?)\*\*', r'\1', references_text)  # Remove bold
                    references_text = re.sub(r'\*(.*?)\*', r'\1', references_text)      # Remove italics
                    references_text = re.sub(r'\\cite{.*?}', '', references_text)       # Remove LaTeX citations
                    references_text = re.sub(r'\\ref{.*?}', '', references_text)        # Remove LaTeX refs
                    references_text = re.sub(r'^\s*\[?\d+[\.\]]\s*', '', references_text, flags=re.MULTILINE)  # Remove reference numbers
                    
                    # Write cleaned text
                    temp_in.write(references_text)
                    temp_in.flush()
                    
                    # Run Anystyle parse command
                    parse_cmd = ['anystyle', '--format', 'json', 'parse', temp_in.name]
                    if self.debug:
                        print(colored(f"Running command: {' '.join(parse_cmd)}", "blue"))
                        print(colored("→ Processing references with Anystyle...", "blue"))
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
                                
                                if self.debug:
                                    print(colored(f"✓ Parsed reference: {reference.title[:50]}...", "green"))
                                    
                            except Exception as e:
                                print(colored(f"⚠️ Error parsing reference: {e}", "yellow"))
                                continue
                        
                        print(colored(f"✓ Successfully parsed {len(references)} references", "green"))
                        return references
                        
                    except json.JSONDecodeError as e:
                        print(colored(f"⚠️ Error decoding JSON from Anystyle output: {e}", "red"))
                        if self.debug:
                            print(colored("Anystyle output:", "yellow"))
                            print(result.stdout)
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
                    print(colored(f"⚠️ Error removing temporary file: {e}", "yellow"))
        
        return references 