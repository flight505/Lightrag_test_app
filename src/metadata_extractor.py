from typing import Dict, Any, Optional, List
from termcolor import colored
import subprocess
import re
import tempfile
import json
import os
from .academic_metadata import Reference, Author, AcademicMetadata

class MetadataExtractor:
    """Extracts metadata from academic documents"""
    
    def __init__(self):
        """Initialize metadata extractor and check Anystyle availability"""
        self.has_anystyle = self._check_anystyle()
        
    def _check_anystyle(self) -> bool:
        """Check if Anystyle is available"""
        try:
            result = subprocess.run(['anystyle', '--version'], capture_output=True, text=True, check=True)
            print(colored(f"✓ Found Anystyle: {result.stdout.strip()}", "green"))
            return True
        except subprocess.CalledProcessError:
            print(colored("⚠️ Anystyle not found. Please install Anystyle CLI: gem install anystyle-cli", "yellow"))
            return False
            
    def _extract_references_with_anystyle(self, text: str) -> List[Reference]:
        """Extract references using Anystyle CLI with two-step process"""
        if not self.has_anystyle:
            print(colored("⚠️ Anystyle not available, skipping reference extraction", "yellow"))
            return []
            
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as temp_in, \
                 tempfile.NamedTemporaryFile(mode='w', suffix='.json', encoding='utf-8', delete=False) as temp_find, \
                 tempfile.NamedTemporaryFile(mode='w', suffix='.json', encoding='utf-8', delete=False) as temp_parse:
                
                # Write text to temporary file
                temp_in.write(text)
                temp_in.flush()
                
                # Step 1: Find references in text
                print(colored("→ Running Anystyle find to locate references...", "blue"))
                find_cmd = ['anystyle', '--format', 'json', '--no-layout', 'find', temp_in.name, temp_find.name]
                subprocess.run(find_cmd, capture_output=True, text=True, check=True)
                
                # Read found references
                with open(temp_find.name, 'r', encoding='utf-8') as f:
                    found_refs = json.load(f)
                
                if not found_refs:
                    print(colored("⚠️ No references found in text", "yellow"))
                    return []
                
                # Write found references to new file for parsing
                refs_text = "\n\n".join(ref.get('text', '') for ref in found_refs)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as temp_refs:
                    temp_refs.write(refs_text)
                    temp_refs.flush()
                    
                    # Step 2: Parse found references
                    print(colored("→ Running Anystyle parse on found references...", "blue"))
                    parse_cmd = ['anystyle', '--format', 'json', 'parse', temp_refs.name, temp_parse.name]
                    subprocess.run(parse_cmd, capture_output=True, text=True, check=True)
                    
                # Read parsed references
                with open(temp_parse.name, 'r', encoding='utf-8') as f:
                    parsed_refs = json.load(f)
                    
                if parsed_refs:
                    # Convert parsed references to Reference objects
                    references = []
                    for ref in parsed_refs:
                        try:
                            # Extract year from date if present
                            year = None
                            if 'date' in ref:
                                date_str = str(ref['date'][0]) if isinstance(ref['date'], list) else str(ref['date'])
                                year_match = re.search(r'\d{4}', date_str)
                                if year_match:
                                    year = int(year_match.group())
                            
                            # Create Reference object
                            reference = Reference(
                                raw_text=ref.get('original', ''),
                                title=ref.get('title', [None])[0] if isinstance(ref.get('title', []), list) else ref.get('title'),
                                authors=[Author(full_name=a) for a in ref.get('author', [])],
                                year=year,
                                doi=ref.get('doi', [None])[0] if isinstance(ref.get('doi', []), list) else ref.get('doi'),
                                venue=ref.get('container-title', [None])[0] if isinstance(ref.get('container-title', []), list) else ref.get('container-title')
                            )
                            references.append(reference)
                        except Exception as err:
                            print(colored(f"⚠️ Error parsing reference: {str(err)}", "yellow"))
                            continue
                            
                    print(colored(f"✓ Successfully parsed {len(references)} references", "green"))
                    return references
                else:
                    print(colored("⚠️ No references parsed", "yellow"))
                    return []
                    
        except Exception as err:
            print(colored(f"⚠️ Error during reference extraction: {str(err)}", "yellow"))
            return []
        finally:
            # Clean up temporary files
            for temp_file in [temp_in.name, temp_find.name, temp_parse.name]:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
                
    def _parse_authors(self, author_data: List[Any]) -> List[Author]:
        """Parse authors with improved filtering for addresses and institutions"""
        authors = []
        
        # Common address/institution keywords to filter out
        address_keywords = {'university', 'department', 'institute', 'school', 'college', 
                           'street', 'road', 'ave', 'boulevard', 'blvd', 'usa', 'uk'}
        
        for author in author_data:
            try:
                full_name = ""
                if isinstance(author, dict):
                    # Handle dictionary input (from Anystyle)
                    given = author.get('given', '')
                    family = author.get('family', '')
                    full_name = f"{given} {family}".strip()
                else:
                    # Handle string input
                    full_name = str(author).strip()
                
                # Skip if empty or looks like an address
                if not full_name or any(keyword in full_name.lower() for keyword in address_keywords):
                    continue
                
                # Create Author object with only full_name
                authors.append(Author(full_name=full_name))
                
            except Exception as err:
                print(colored(f"⚠️ Error parsing author: {str(err)}", "yellow"))
                continue
            
        return authors
        
    def extract_metadata(self, text: str, doc_id: str, pdf_path: Optional[str] = None, existing_metadata: Optional[Dict] = None) -> AcademicMetadata:
        """Extract metadata including references using Anystyle"""
        try:
            # Create base metadata object
            metadata = AcademicMetadata(doc_id=doc_id)
            
            # If we have existing metadata, use it as a base
            if existing_metadata:
                print(colored(f"✓ Using existing metadata from {existing_metadata.get('source', 'unknown')}", "green"))
                
                metadata.title = existing_metadata.get('title', '')
                metadata.abstract = existing_metadata.get('abstract', '')
                
                # Handle authors - only use full_name to avoid 'given' keyword error
                authors = []
                for author_data in existing_metadata.get('authors', []):
                    try:
                        if isinstance(author_data, dict):
                            # Combine given and family names for full_name
                            given = author_data.get('given', '')
                            family = author_data.get('family', '')
                            full_name = f"{given} {family}".strip()
                            if full_name:
                                authors.append(Author(full_name=full_name))
                        elif isinstance(author_data, Author):
                            authors.append(author_data)
                        elif isinstance(author_data, str):
                            authors.append(Author(full_name=author_data))
                    except Exception as err:
                        print(colored(f"⚠️ Error creating author object: {str(err)}", "yellow"))
                        continue
                
                metadata.authors = authors
            
            # Extract references using Anystyle
            print(colored("\n=== Extracting References with Anystyle ===", "blue"))
            references = self._extract_references_with_anystyle(text)
            metadata.references = references
            
            return metadata
            
        except Exception as err:
            print(colored(f"⚠️ Error extracting metadata: {str(err)}", "yellow"))
            # Return empty metadata object rather than None
            return AcademicMetadata(doc_id=doc_id) 