## Project Overview
The LightRAG application is a sophisticated academic research tool that combines knowledge graph capabilities with retrieval-augmented generation (RAG). Key features include:

- **Advanced PDF Processing**: Uses Marker, PyMuPDF, or PyPDF2 (configurable through PDFEngine enum)
- **Equation Handling**: Extracts and processes LaTeX equations with symbol extraction
- **Reference Management**: Citation pattern matching and reference tracking with CrossRef/arXiv integration
- **Multi-Mode Search**: Supports Naive, Local, Global, Hybrid, and Mix search modes
- **Academic Response Processing**: Formats responses with citations and equation formatting
- **Metadata Management**: JSON-based metadata storage with automatic updates

### Critical Dependencies
- **Anystyle**: Required for reference extraction (Ruby gem, not Python package)
- **Marker**: Primary PDF converter, requires proper initialization
- **pdf2doi**: Used for DOI/arXiv identifier extraction
- **CrossRef/arXiv APIs**: Used for metadata enrichment
- **LightRAG**: Core RAG functionality (version >= 1.1.0)
- **OpenAI API**: Required for completion endpoints

### Breaking Points
1. **PDF Processing**:
   - Marker initialization failures will break PDF processing
   - PyMuPDF (fitz) import must use pymupdf package
   - PDF file size limits (default 50MB)
   - Invalid UTF-8 encoding in PDFs

2. **Metadata Extraction**:
   - Missing Anystyle installation
   - Failed DOI/arXiv extraction
   - API rate limits (CrossRef/arXiv)
   - Invalid JSON in metadata files

3. **Reference Processing**:
   - Malformed citation patterns
   - Missing reference sections
   - Invalid DOIs or arXiv IDs
   - Failed API lookups

4. **Equation Processing**:
   - Malformed LaTeX equations
   - Missing equation delimiters ($$)
   - Symbol extraction failures

## Core Processing Systems

### Reference Processing System
1. **Extraction Pipeline**:
   ```
   PDF -> pdf2doi -> DOI/arXiv ID -> CrossRef/arXiv API -> Metadata
                  -> Anystyle -> Raw References -> Reference Objects
   ```
   - pdf2doi extracts DOI or arXiv identifier
   - If DOI found: Use CrossRef API for metadata
   - If arXiv ID found: Use arXiv API for metadata
   - Anystyle processes raw reference text regardless of API results
   - Results are merged with priority to API data

2. **Reference Object Structure**:
   ```python
   class Reference:
       raw_text: str
       title: Optional[str]
       authors: List[Author]
       year: Optional[int]
       doi: Optional[str]
       venue: Optional[str]
   ```

3. **Reference Validation**:
   - Basic: Checks for required fields
   - Standard: Validates DOI/URLs
   - Strict: Verifies all fields and cross-references

### Citation Processing System
1. **Citation Pattern Recognition**:
   ```python
   PATTERNS = {
       'numeric': [
           r'\[(\d+(?:\s*,\s*\d+)*)\]',  # [1] or [1,2,3]
           r'\[(\d+\s*-\s*\d+)\]'        # [1-3]
       ],
       'author_year': [
           r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)'  # Smith et al. (2023)
       ],
       'cross_ref': [
           r'cf\.\s+([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)'  # cf. Smith et al. (2023)
       ]
   }
   ```

2. **Citation Context Extraction**:
   - Extracts window of text around citation (default 100 chars)
   - Tracks citation location (paragraph and offset)
   - Preserves citation style and formatting

3. **Citation-Reference Linking**:
   ```python
   class CitationLink:
       citation_text: str
       reference: Reference
       context: str
       location: CitationLocation
   ```

4. **Citation Graph Generation**:
   - Builds directed graph of citations
   - Tracks citation frequency and patterns
   - Enables network visualization
   - Supports citation validation

### Equation Processing System
1. **Equation Detection**:
   ```python
   EQUATION_PATTERNS = [
       (r'\$\$(.*?)\$\$', EquationType.DISPLAY),             # Display equations
       (r'\$(.*?)\$', EquationType.INLINE),                  # Inline equations
       (r'\\begin\{equation\}(.*?)\\end\{equation\}', EquationType.DISPLAY),
       (r'\\[(.*?)\\]', EquationType.DISPLAY),
       (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', EquationType.DISPLAY),
       (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', EquationType.DISPLAY)
   ]
   ```

2. **Symbol Extraction**:
   ```python
   SYMBOL_PATTERNS = [
       r'\\alpha', r'\\beta', r'\\gamma', r'\\delta',    # Greek letters
       r'\\sum', r'\\prod', r'\\int',                    # Operators
       r'\\frac', r'\\sqrt', r'\\partial',               # Functions
       r'\\mathcal', r'\\mathbf', r'\\mathrm'           # Styles
   ]
   ```

3. **Equation Object Structure**:
   ```python
   class Equation:
       raw_text: str
       symbols: Set[str]
       equation_type: EquationType
       context: Optional[str]
   ```

4. **Equation Classification**:
   - INLINE: Within text equations
   - DISPLAY: Standalone equations
   - DEFINITION: Mathematical definitions
   - THEOREM: Mathematical theorems

### Integration Flow
1. **Document Processing**:
   ```
   PDF Document
   ├── Text Extraction (Marker/PyMuPDF/PyPDF2)
   ├── Metadata Extraction
   │   ├── DOI/arXiv Processing
   │   └── API Enrichment
   ├── Reference Processing
   │   ├── Anystyle Extraction
   │   └── Reference Object Creation
   ├── Citation Processing
   │   ├── Pattern Matching
   │   ├── Context Extraction
   │   └── Reference Linking
   └── Equation Processing
       ├── Pattern Detection
       ├── Symbol Extraction
       └── Classification
   ```

2. **Data Storage**:
   ```
   store_name/
   ├── metadata.json         # Document metadata
   ├── converted/
   │   ├── doc1.txt         # Converted text
   │   └── doc1.md          # Markdown version
   └── cache/
       ├── embeddings/      # Vector embeddings
       └── api_responses/   # API response cache
   ```

3. **Validation Chain**:
   - File validation (size, encoding)
   - Content extraction validation
   - Reference validation
   - Citation validation
   - Equation validation

## Core Components

1. **AcademicMetadata**:
   - Structured metadata using Pydantic models
   - Automatic validation and type checking
   - Handles Authors, References, Citations, Equations
   - JSON serialization with model_dump methods

2. **FileProcessor**:
   - PDF Processing Pipeline:
     1. File validation and size checks
     2. PDF conversion using selected engine
     3. Metadata extraction (DOI/arXiv)
     4. Reference extraction (Anystyle)
     5. Equation extraction
     6. JSON metadata storage

3. **PDFConverter**:
   - Factory pattern for converter selection
   - Supported engines: Marker, PyMuPDF, PyPDF2
   - Fallback chain for robustness
   - Enhanced equation detection

4. **CitationProcessor**:
   - Pattern matching for multiple citation styles
   - Context extraction around citations
   - Citation graph generation
   - Citation validation

5. **EquationExtractor**:
   - LaTeX equation detection
   - Symbol extraction and classification
   - Equation type detection
   - Context preservation

6. **MetadataExtractor**:
   - DOI/arXiv identifier extraction
   - CrossRef/arXiv API integration
   - Reference parsing with Anystyle
   - Metadata consolidation

## Configuration

1. **ProcessingConfig**:
   ```python
   pdf_engine: PDFEngine = PDFEngine.AUTO
   enable_crossref: bool = True
   enable_scholarly: bool = True
   debug_mode: bool = False
   max_file_size_mb: int = 50
   timeout_seconds: int = 30
   chunk_size: int = 500
   chunk_overlap: int = 50
   chunk_strategy: str = "sentence"
   ```

2. **Search Modes**:
   - naive: Basic text search
   - local: Context-aware search
   - global: Knowledge base search
   - hybrid: Combined search
   - mix: Adaptive strategy

## Best Practices
1. **File Operations**:
   - Always use UTF-8 encoding
   - Handle file paths with Path objects
   - Validate file existence before operations
   - Clean up temporary files

2. **Error Handling**:
   - Use try-except blocks with specific exceptions
   - Log errors with termcolor
   - Provide user feedback
   - Graceful fallbacks

3. **API Usage**:
   - Handle rate limits
   - Cache responses when possible
   - Validate API responses
   - Use async where available

4. **Performance**:
   - Lazy initialization of heavy components
   - Cache frequently used data
   - Use appropriate chunk sizes
   - Monitor memory usage

## UI Components
- Streamlit-based interface
- Dark mode with Dracula theme
- Progress indicators
- Interactive visualizations
- Citation network graphs
- Equation rendering

## Directory Structure
```
project/
├── src/
│   ├── academic_metadata.py
│   ├── citation_metadata.py
│   ├── equation_metadata.py
│   ├── file_processor.py
│   ├── pdf_converter.py
│   └── metadata_extractor.py
├── pages/
│   ├── Home.py
│   ├── Search.py
│   ├── Manage.py
│   └── Academic.py
├── tests/
│   ├── test_metadata.py
│   └── test_citation_processor.py
└── DB/
    └── store_name/
        ├── metadata.json
        ├── converted/
        └── cache/
```

## Class Relationships and Imports

### Core Classes and Their Locations
1. **Base Classes** (`base_metadata.py`):
   ```python
   class Author:
       full_name: Optional[str]
       first_name: Optional[str]
       last_name: Optional[str]
       affiliation: Optional[str]
       email: Optional[str]
       orcid: Optional[str]

   class Reference:
       raw_text: str
       title: Optional[str]
       authors: List[Author]
       year: Optional[int]
       doi: Optional[str]
       venue: Optional[str]
   ```

2. **Academic Classes** (`academic_metadata.py`):
   ```python
   from .base_metadata import Author, Reference
   
   class Citation:
       text: str
       references: List[Reference]
       context: str
   
   class AcademicMetadata:
       title: str
       authors: List[Author]
       abstract: Optional[str]
       references: List[Reference]
       citations: List[Citation]
       equations: List[str]  # References equations from equation_metadata
   ```

3. **Equation Classes** (`equation_metadata.py`):
   ```python
   class EquationType(str, Enum):
       INLINE = "inline"
       DISPLAY = "display"
       DEFINITION = "definition"
       THEOREM = "theorem"
   
   class Equation:
       raw_text: str
       symbols: Set[str]
       equation_type: EquationType
       context: Optional[str]
   ```

4. **Citation Classes** (`citation_metadata.py`):
   ```python
   from .base_metadata import Author, Reference
   
   class CitationLocation:
       paragraph: int
       offset: int
   
   class CitationLink:
       citation_text: str
       reference: Reference
       context: str
       location: CitationLocation
   ```

### Import Guidelines
1. **Base Classes**:
   - Always import Author and Reference from base_metadata
   - These are the foundation for all metadata objects

2. **Equations**:
   - Import Equation and EquationType from equation_metadata
   - Never import from academic_metadata

3. **Citations**:
   - Import Citation classes from citation_metadata
   - Use base_metadata for Author/Reference dependencies

4. **Academic Metadata**:
   - Import AcademicMetadata from academic_metadata
   - This class ties together all other components

### Common Import Patterns
```python
# Correct imports
from src.base_metadata import Author, Reference
from src.equation_metadata import Equation, EquationType
from src.citation_metadata import CitationLink, CitationLocation
from src.academic_metadata import AcademicMetadata, Citation

# Incorrect imports (will cause errors)
from src.academic_metadata import Equation  # Wrong! Import from equation_metadata
from src.citation_metadata import Reference  # Wrong! Import from base_metadata