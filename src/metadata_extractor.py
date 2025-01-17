import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader
from termcolor import colored

from .academic_metadata import AcademicMetadata, Citation
from .base_metadata import Author, Reference
from .equation_metadata import Equation, EquationExtractor
from .citation_metadata import CitationProcessor

logger = logging.getLogger(__name__)


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
        """Extract title from text."""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Common patterns to skip
            skip_patterns = [
                'open', '## open', '## **open**',
                'contents lists available',
                'image', 'figure', 'table',
                'received:', 'accepted:', 'published:', 'doi:', '@', 'university',
                'available online', 'sciencedirect', 'elsevier',
                'journal', 'volume', 'issue'
            ]
            
            # First try to find a markdown title with #
            for i, line in enumerate(lines):
                if line.startswith(('#', '##')):
                    clean_line = re.sub(r'[#*]', '', line).strip()
                    
                    if any(skip in clean_line.lower() for skip in skip_patterns):
                        continue
                        
                    if re.match(r'^[\d\.]+\s', clean_line):
                        continue
                    
                    return clean_line
            
            # If no markdown title, try first non-skipped line
            for line in lines[:10]:  # Only check first 10 lines
                if any(skip in line.lower() for skip in skip_patterns):
                    continue
                    
                if len(line.split()) <= 3:
                    continue
                    
                digit_ratio = sum(c.isdigit() for c in line) / len(line)
                if digit_ratio >= 0.2:
                    continue
                    
                special_char_ratio = sum(not c.isalnum() and not c.isspace() for c in line) / len(line)
                if special_char_ratio >= 0.1:
                    continue
                
                return line
            
            return None
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting title: {str(e)}", "yellow"))
            return None
            
    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from text."""
        try:
            lines = text.split('\n')
            abstract = ""
            abstract_start = -1
            
            # Look for abstract header
            for i, line in enumerate(lines):
                if re.match(r'^(?:abstract|summary)[\s:]*$', line.lower()):
                    abstract_start = i
                    break
                elif re.match(r'^[\*#\s]*(?:abstract|summary)[\*\s:]*$', line.lower()):
                    abstract_start = i
                    break
            
            if abstract_start != -1:
                abstract_lines = []
                for line in lines[abstract_start + 1:]:
                    if any(marker in line.lower() for marker in ['introduction', 'keywords', '1.', 'background']):
                        break
                    if line.strip():
                        abstract_lines.append(line.strip())
                abstract = ' '.join(abstract_lines)
            
            return abstract if abstract else None
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting abstract: {str(e)}", "yellow"))
            return None

    def _parse_from_text(self, text: str, doc_id: str) -> Optional[AcademicMetadata]:
        """Parse metadata from text when API extraction fails"""
        try:
            # Extract title from first line
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            title = lines[0] if lines else ''
            
            # Extract authors from second line
            authors = []
            if len(lines) > 1:
                author_line = lines[1].strip()
                author_names = [name.strip() for name in author_line.split(',')]
                for name in author_names:
                    if name:
                        parts = name.split()
                        if len(parts) > 1:
                            first_name = ' '.join(parts[:-1])
                            last_name = parts[-1]
                            authors.append(Author(
                                full_name=name,
                                first_name=first_name,
                                last_name=last_name
                            ))
                        else:
                            authors.append(Author(full_name=name, last_name=name))
            
            # Extract year using regex
            year = None
            year_match = re.search(r'\b(19|20)\d{2}\b', text)
            if year_match:
                year = int(year_match.group())
                
            # Extract references
            references = []
            if self.anystyle_available:
                references = self._extract_references_with_anystyle(text)
                
            # Extract equations
            equations = self.equation_extractor.extract_equations(text)
            
            return AcademicMetadata(
                doc_id=doc_id,
                title=title,
                authors=authors,
                abstract='',
                references=references,
                year=year,
                equations=equations,
                source='text'
            )
            
        except Exception as e:
            print(colored(f"⚠️ Error parsing from text: {str(e)}", "yellow"))
            return AcademicMetadata(doc_id=doc_id)

    def extract_metadata(self, text: str, doc_id: str, pdf_path: Optional[str] = None, existing_metadata: Dict = None) -> AcademicMetadata:
        """Extract academic metadata from text and PDF, reusing existing metadata if available"""
        try:
            # Extract equations first
            equations = self.equation_extractor.extract_equations(text)
            if equations:
                print(colored(f"✓ Found {len(equations)} equations", "green"))

            # If we have existing metadata from arXiv or DOI, use it but add references and equations
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
                
                # Extract references section from text
                references_text = self._extract_references_section(text)
                references = []
                if references_text and self.anystyle_available:
                    print(colored("→ Extracting references with Anystyle...", "blue"))
                    references = self._parse_references(references_text)
                    if references:
                        print(colored(f"✓ Found {len(references)} references", "green"))
                
                # Process citations if we have references
                citations = []
                if references:
                    print(colored("→ Processing citations...", "blue"))
                    citation_processor = CitationProcessor(references=references)
                    citation_links = citation_processor.process_citations(text)
                    if citation_links:
                        citations = [link.to_citation() for link in citation_links]
                        print(colored(f"✓ Found {len(citations)} citations", "green"))
                
                # If abstract is missing, try to extract from text
                abstract = existing_metadata.get('abstract', '')
                if not abstract:
                    abstract = self._extract_abstract(text) or ''
                
                return AcademicMetadata(
                    doc_id=doc_id,
                    title=existing_metadata.get('title', ''),
                    authors=authors,
                    abstract=abstract,  # Use extracted abstract if needed
                    references=references,
                    citations=citations,
                    equations=equations,
                    identifier=existing_metadata.get('identifier'),
                    identifier_type=existing_metadata.get('identifier_type'),
                    journal=existing_metadata.get('journal'),
                    source=existing_metadata.get('source'),
                    year=existing_metadata.get('year')
                )
            
            # Extract metadata from scratch
            title = self._extract_title(text)
            authors = self._extract_authors(text)
            abstract = self._extract_abstract(text)
            references = []
            citations = []
            
            # Extract references if available
            references_text = self._extract_references_section(text)
            if references_text and self.anystyle_available:
                print(colored("→ Extracting references with Anystyle...", "blue"))
                references = self._parse_references(references_text)
                if references:
                    print(colored(f"✓ Found {len(references)} references", "green"))
                    
                    # Process citations if we have references
                    print(colored("→ Processing citations...", "blue"))
                    citation_processor = CitationProcessor(references=references)
                    citation_links = citation_processor.process_citations(text)
                    if citation_links:
                        citations = [link.to_citation() for link in citation_links]
                        print(colored(f"✓ Found {len(citations)} citations", "green"))
            
            # Create and return AcademicMetadata object
            return AcademicMetadata(
                doc_id=doc_id,
                title=title or '',
                authors=authors,
                abstract=abstract or '',
                references=references,
                citations=citations,
                equations=equations
            )
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting metadata: {str(e)}", "red"))
            # Return empty metadata object on error
            return AcademicMetadata(doc_id=doc_id)

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
                        for ref in references_data:
                            try:
                                # Extract year from date if present
                                year = None
                                if 'date' in ref:
                                    year_match = re.search(r'\b\d{4}\b', str(ref['date'][0]) if isinstance(ref['date'], list) else str(ref['date']))
                                    if year_match:
                                        year = int(year_match.group())
                                
                                # Extract authors
                                authors = []
                                if 'author' in ref:
                                    author_list = ref['author'] if isinstance(ref['author'], list) else [ref['author']]
                                    for author in author_list:
                                        if isinstance(author, dict):
                                            # Handle structured author data
                                            full_name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                                            authors.append(Author(full_name=full_name))
                                        else:
                                            # Handle string author data
                                            authors.append(Author(full_name=str(author)))
                                
                                # Create Reference object
                                reference = Reference(
                                    raw_text=ref.get('original', ''),
                                    title=ref.get('title', [''])[0] if isinstance(ref.get('title'), list) else ref.get('title', ''),
                                    authors=authors,
                                    year=year,
                                    doi=ref.get('doi', [''])[0] if isinstance(ref.get('doi'), list) else ref.get('doi', ''),
                                    venue=ref.get('journal', [''])[0] if isinstance(ref.get('journal'), list) else ref.get('journal', '')
                                )
                                references.append(reference)
                            except Exception as e:
                                print(colored(f"⚠️ Error parsing reference: {e}", "yellow"))
                                continue
                            
                        print(colored(f"✓ Successfully parsed {len(references)} references", "green"))
                    except json.JSONDecodeError as e:
                        print(colored(f"⚠️ Error decoding JSON from Anystyle output: {e}", "red"))
                        
            except Exception as e:
                print(colored(f"⚠️ Error processing references with Anystyle: {e}", "yellow"))
            
        return references 

    def _extract_references_section(self, text: str) -> Optional[str]:
        """Extract the references section from text."""
        try:
            # Try to find references section using different patterns
            patterns = [
                r'(?i)^#+\s*\**references\**\s*$\n(.*?)(?=^#+|\Z)',  # Markdown headers with optional asterisks
                r'(?i)^references$\n-+\n(.*?)(?=\n\n\w|\Z)',  # Underlined style
                r'(?i)\[\s*references\s*\]\n(.*?)(?=\n\[|\Z)',  # Bracketed style
                r'(?i)(?:bibliography|works cited|citations)\n(.*?)(?=\n\n\w|\Z)'  # Alternative headers
            ]
            
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
                    return references_text
            
            # Fallback: try to find numbered references directly
            numbered_pattern = r'(?m)^\s*(?:\[?\d+[\.\]]\s+|\d+\.\s+)(.*?)(?=^\s*(?:\[?\d+[\.\]]\s+|\d+\.\s+)|\Z)'
            matches = re.findall(numbered_pattern, text, re.DOTALL | re.MULTILINE)
            if matches:
                references_text = '\n'.join(matches)
                if self.debug:
                    print(colored("✓ Found references using numbered pattern fallback", "green"))
                    match_count = len(matches)
                    print(colored(f"→ Found {match_count} numbered references", "blue"))
                return references_text
            
            print(colored("⚠️ No references section found in text", "yellow"))
            return None
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting references section: {str(e)}", "yellow"))
            return None

    def _parse_references(self, text: str) -> List[Reference]:
        """Parse references from text using Anystyle."""
        references = []
        try:
            # Clean up reference text
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
            text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italics
            text = re.sub(r'\\cite{.*?}', '', text)       # Remove LaTeX citations
            text = re.sub(r'\\ref{.*?}', '', text)        # Remove LaTeX refs
            text = re.sub(r'^\s*\[?\d+[\.\]]\s*', '', text, flags=re.MULTILINE)  # Remove reference numbers
            
            # Write to temp file for Anystyle
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_in:
                temp_in.write(text)
                temp_in.flush()
                
                # Run Anystyle parse command
                parse_cmd = ['anystyle', '--format', 'json', 'parse', temp_in.name]
                if self.debug:
                    print(colored(f"Running command: {' '.join(parse_cmd)}", "blue"))
                    print(colored("→ Processing references with Anystyle...", "blue"))
                result = subprocess.run(parse_cmd, capture_output=True, text=True, check=True)
                
                try:
                    references_data = json.loads(result.stdout)
                    for ref in references_data:
                        try:
                            # Extract year from date if present
                            year = None
                            if 'date' in ref:
                                year_match = re.search(r'\b\d{4}\b', str(ref['date'][0]) if isinstance(ref['date'], list) else str(ref['date']))
                                if year_match:
                                    year = int(year_match.group())
                            
                            # Extract authors
                            authors = []
                            if 'author' in ref:
                                author_list = ref['author'] if isinstance(ref['author'], list) else [ref['author']]
                                for author in author_list:
                                    if isinstance(author, dict):
                                        # Handle structured author data
                                        full_name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                                        authors.append(Author(full_name=full_name))
                                    else:
                                        # Handle string author data
                                        authors.append(Author(full_name=str(author)))
                            
                            # Create Reference object
                            reference = Reference(
                                raw_text=ref.get('original', ''),
                                title=ref.get('title', [''])[0] if isinstance(ref.get('title'), list) else ref.get('title', ''),
                                authors=authors,
                                year=year,
                                doi=ref.get('doi', [''])[0] if isinstance(ref.get('doi'), list) else ref.get('doi', ''),
                                venue=ref.get('journal', [''])[0] if isinstance(ref.get('journal'), list) else ref.get('journal', '')
                            )
                            references.append(reference)
                        except Exception as e:
                            print(colored(f"⚠️ Error parsing reference: {e}", "yellow"))
                            continue
                            
                    print(colored(f"✓ Successfully parsed {len(references)} references", "green"))
                except json.JSONDecodeError as e:
                    print(colored(f"⚠️ Error decoding JSON from Anystyle output: {e}", "red"))
                    
        except Exception as e:
            print(colored(f"⚠️ Error processing references with Anystyle: {e}", "yellow"))
            
        return references

    def _extract_authors(self, text: str) -> List[Author]:
        """Extract authors from text."""
        authors = []
        try:
            lines = text.split('\n')
            
            # Look for author section after title
            title_index = -1
            for i, line in enumerate(lines):
                if line.startswith(('#', '##')) or (i < 10 and len(line.split()) > 3):
                    title_index = i
                    break
            
            if title_index != -1:
                # Look at next few lines for authors
                for i in range(title_index + 1, min(title_index + 5, len(lines))):
                    line = lines[i].strip()
                    
                    # Skip empty lines and non-author content
                    if not line or any(skip in line.lower() for skip in ['abstract', 'introduction', 'keywords', 'received']):
                        continue
                    
                    # Look for lines with author-like patterns
                    if (',' in line or ' & ' in line or ' and ' in line.lower() or '**' in line or 'M.D.' in line):
                        # Clean the line
                        author_line = line.replace('**', '').strip()
                        
                        # Handle affiliations marked with numbers
                        author_line = re.sub(r'\d+\s*$', '', author_line)
                        author_line = re.sub(r'\s*,\s*M\.D\.', '', author_line)
                        author_line = re.sub(r'\s*,\s*Ph\.D\.', '', author_line)
                        author_line = re.sub(r'\s*,\s*M\.P\.H\.', '', author_line)
                        
                        # Split on common separators
                        for sep in [' and ', ' & ', ',']:
                            author_line = author_line.replace(sep, '|')
                        author_names = [name.strip() for name in author_line.split('|') if name.strip()]
                        
                        for name in author_names:
                            if len(name) < 3:
                                continue
                                
                            if '@' in name:
                                continue
                                
                            if any(word in name.lower() for word in ['university', 'department', 'division']):
                                continue
                            
                            # Clean the name
                            name = re.sub(r'[\(\)\[\]\{\}\d]', '', name).strip()
                            # Remove degrees and titles
                            name = re.sub(r'\s*(?:M\.D\.|Ph\.D\.|M\.P\.H\.|Professor|Dr\.|Prof\.)\s*', '', name)
                            parts = [p for p in name.split() if len(p) > 1]
                            
                            if parts:
                                author = Author(
                                    full_name=name,
                                    first_name=parts[0],
                                    last_name=parts[-1]
                                )
                                authors.append(author)
                        
                        if authors:  # If we found authors, stop looking
                            break
            
            return authors
            
        except Exception as e:
            print(colored(f"⚠️ Error extracting authors: {str(e)}", "yellow"))
            return []

