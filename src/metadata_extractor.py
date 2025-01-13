from typing import Dict, Any, Optional, List
from termcolor import colored
import subprocess
import re
import tempfile
import json
import os
from .academic_metadata import Reference, Author

class MetadataExtractor:
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

    def extract_metadata(self, text: str, doc_id: str, pdf_path: str = None, existing_metadata: Dict = None) -> Dict[str, Any]:
        """Extract academic metadata from text and PDF, reusing existing metadata if available"""
        try:
            # Initialize with existing metadata if provided
            metadata = existing_metadata or {}
            
            # If we have existing metadata from arXiv or DOI, use it but still extract references
            if existing_metadata and existing_metadata.get('source') in ['arxiv', 'crossref']:
                print(colored(f"✓ Using existing {existing_metadata['source']} metadata", "green"))
                metadata = existing_metadata.copy()
            else:
                # Only extract basic metadata if we don't have it
                if not metadata.get('title'):
                    metadata['title'] = self._extract_title(text)
                if not metadata.get('authors'):
                    metadata['authors'] = self._extract_authors(text)
                if not metadata.get('abstract'):
                    metadata['abstract'] = self._extract_abstract(text)
            
            # Always try to extract references using Anystyle
            if not metadata.get('references') and self.anystyle_available:
                print(colored("→ Extracting references with Anystyle...", "blue"))
                references_text = self._extract_references_section(text)
                if references_text:
                    references = self._parse_references(references_text)
                    if references:
                        metadata['references'] = [ref.to_dict() for ref in references]
                        print(colored(f"✓ Extracted {len(references)} references with Anystyle", "green"))
                    else:
                        print(colored("⚠️ No references found by Anystyle", "yellow"))
                else:
                    print(colored("⚠️ No references section found in text", "yellow"))
            
            # Extract citations if not present
            if not metadata.get('citations'):
                metadata['citations'] = self._extract_citations(text)
            
            return metadata
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting metadata: {str(e)}", "red"))
            return {}

    def _extract_references_section(self, text: str) -> Optional[str]:
        """Extract the references section from text, supporting both PDF and markdown formats"""
        try:
            lines = text.split('\n')
            references_start = -1
            references_end = len(lines)
            
            # Enhanced pattern for markdown and PDF formats
            ref_patterns = [
                r'^[\*#\s]*(?:references|bibliography|works cited|citations)[\*\s]*$',
                r'^(?:References|Bibliography|Works Cited|Citations)[\s:]*$',
                r'^[\d\s\.]*(?:References|Bibliography|Works Cited|Citations)[\s:]*$'
            ]
            
            # Find references section start
            for i, line in enumerate(lines):
                if any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in ref_patterns):
                    references_start = i + 1  # Skip the header
                    print(colored("✓ Found references section header", "green"))
                    break
            
            if references_start == -1:
                return None
            
            # Find references section end (next major section or end of file)
            for i in range(references_start, len(lines)):
                if re.match(r'^[\*#\s]*(?:appendix|acknowledgments?|supplementary|notes?|about|author)[\*\s]*$', lines[i].lower()):
                    references_end = i
                    break
                # Also stop at markdown horizontal rules
                if re.match(r'^[\s]*[-*_]{3,}[\s]*$', lines[i]):
                    references_end = i
                    break
            
            references_text = '\n'.join(lines[references_start:references_end])
            if not references_text.strip():
                return None
                
            print(colored(f"✓ Extracted references section ({references_end - references_start} lines)", "green"))
            return references_text
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting references section: {str(e)}", "yellow"))
            return None 

    def _parse_references(self, text: str) -> List[Reference]:
        """Parse references using Anystyle CLI with enhanced error handling"""
        references = []
        if not self.anystyle_available:
            print(colored("⚠️ Anystyle not available - skipping reference parsing", "yellow"))
            return references
            
        try:
            # Write references to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('\n'.join(text.split('\n')) if isinstance(text, list) else text)
                temp_path = f.name
            
            try:
                # Run anystyle parse command with JSON output
                cmd = ["anystyle", "--format", "json", "parse", temp_path]
                print(colored("→ Running Anystyle on references section...", "blue"))
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout:
                    try:
                        parsed_refs = json.loads(result.stdout)
                        for ref in parsed_refs:
                            try:
                                # Handle date/year parsing
                                year = None
                                if 'date' in ref:
                                    date_str = str(ref['date'][0]) if isinstance(ref['date'], list) else str(ref['date'])
                                    year_match = re.search(r'\d{4}', date_str)
                                    if year_match:
                                        year = int(year_match.group())
                                
                                # Create reference object
                                reference = Reference(
                                    raw_text=ref.get('original', ''),
                                    title=ref.get('title', [None])[0] if isinstance(ref.get('title', []), list) else ref.get('title'),
                                    authors=self._parse_authors(ref.get('author', [])),
                                    year=year,
                                    doi=ref.get('doi', [None])[0] if isinstance(ref.get('doi', []), list) else ref.get('doi'),
                                    venue=ref.get('container-title', [None])[0] if isinstance(ref.get('container-title', []), list) else ref.get('container-title')
                                )
                                references.append(reference)
                            except Exception as e:
                                print(colored(f"⚠️ Error parsing reference: {str(e)}", "yellow"))
                                continue
                                
                        print(colored(f"✓ Successfully parsed {len(references)} references with Anystyle", "green"))
                    except json.JSONDecodeError as e:
                        print(colored(f"⚠️ Error decoding Anystyle output: {str(e)}", "yellow"))
                else:
                    print(colored(f"⚠️ Anystyle command failed: {result.stderr}", "yellow"))
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                    
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