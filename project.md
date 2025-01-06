## Project Overview
The LightRAG application is a sophisticated academic research tool that combines knowledge graph capabilities with retrieval-augmented generation (RAG). Key features include:

- **Advanced PDF Processing**: Uses Marker with M3 Max optimizations for high-quality PDF conversion
- **Equation Handling**: Extracts and processes LaTeX equations with unique identifiers and context
- **Reference Management**: Advanced citation pattern matching and reference tracking with validation
- **Multi-Mode Search**: Supports Naive, Local, Global, Hybrid, and Mix search modes
- **Academic Response Processing**: Formats responses in academic style with source tracking
- **Metadata Management**: Comprehensive tracking of document metadata, equations, and references

## Core Components

1. **AcademicMetadata** (`src/academic_metadata.py`):
   - Structured metadata extraction from PDFs
   - Author, reference, and equation tracking
   - Multiple citation style support (APA, MLA, Chicago, IEEE)
   - Validation system with configurable levels
   - Equation context and symbol tracking
   - JSON serialization and persistence

2. **FileProcessor** (`src/file_processor.py`):
   - PDF Processing Workflow:
     1. Metadata Extraction: Uses PyMuPDF (primary) and PyPDF2 (fallback) to extract native PDF metadata (title, authors, creation date)
     2. Text Extraction: Employs Marker (optimized for M3 Max) to convert PDFs while preserving layout, equations, and figures
     3. Academic Metadata Processing: Analyzes extracted text to identify and structure:
        - References (using Anystyle - a critical tool for accurate reference extraction)
        - Citations
        - LaTeX equations
        - Author affiliations
        - Abstract
     4. Results Integration: Combines all extracted data into a unified document representation
   
   Purpose: Ensures high-quality PDF processing while preserving academic content integrity, maintaining source files for reference, and enabling sophisticated search and analysis capabilities.
   
   Features:
   - Optimized Marker configuration for M3 Max
   - Fallback extraction chain for robustness
   - Progress tracking for batch operations
   - Source file preservation for validation
   - Comprehensive error handling

3. **FileManager** (`src/file_manager.py`):
   - Database directory structure management
   - Store creation and organization
   - DB root directory gitignore management
   - Metadata file initialization
   - Directory movement and cleanup utilities

4. **LightRAGManager** (`src/lightrag_init.py`):
   - Core RAG functionality with OpenAI integration
   - Multiple model support (gpt-4o, gpt-4o-mini, o1-mini, o1)
   - Configurable chunking strategies
   - Document validation and indexing
   - Query processing with temperature control

5. **DocumentValidator** (`src/document_validator.py`):
   - File and content validation
   - Store structure verification
   - Error reporting and logging

6. **AcademicResponseProcessor** (`src/academic_response_processor.py`):
   - Academic formatting of responses
   - Source tracking and citation management
   - Structured response generation
   - Context-aware reference handling

7. **LightRAG Helpers** (`src/lightrag_helpers.py`):
   - Helper functions for response processing
   - Source management utilities
   - LaTeX equation handling

## Technical Specifications

- **Models**: 
  - Default: gpt-4o-mini
  - Supported: gpt-4o, gpt-4o-mini, o1-mini, o1
  
- **Search Modes**:
  - Naive: Basic search functionality
  - Local: Context-aware local search
  - Global: Broad knowledge base search
  - Hybrid: Combined local and global search
  - Mix: Adaptive search strategy

- **Metadata Processing**:
  - Multiple validation levels (Basic, Standard, Strict)
  - Equation type classification (Inline, Display, Definition, Theorem)
  - Author affiliation tracking
  - DOI and venue extraction
  - Citation network analysis

- **Configuration**:
  - Default chunk size: 500
  - Default chunk overlap: 50
  - Configurable temperature settings
  - Sentence-based chunking strategy

## Error Handling and Logging
- Comprehensive try-except blocks throughout
- Detailed logging with termcolor output
- Progress tracking with stqdm
- Informative error messages with context

## File Management
- UTF-8 encoding for all file operations
- Automatic metadata tracking
- Source file preservation
- Cleanup utilities for unused files

## Best Practices
- Separation of concerns across modules
- Comprehensive error handling
- Progress tracking and user feedback
- Optimized PDF processing for M3 Max
- Environment variable based configuration
- Parallel processing where applicable

## Performance Features
- Optimized PDF conversion settings
- Batch processing capabilities
- Parallel document processing
- Efficient metadata management
- Caching mechanisms for frequent operations

## PDF Processing Pipeline

## Components

### FileProcessor (`src/file_processor.py`)
Handles the complete PDF processing workflow:
1. Metadata Extraction: Uses PyMuPDF (primary) and PyPDF2 (fallback) to extract native PDF metadata (title, authors, creation date)
2. Text Extraction: Uses Marker (optimized for M3) to convert PDFs while preserving layout, equations, and figures
3. Academic Metadata Processing: Analyzes extracted text to identify and structure:
   - References (using Anystyle - a critical tool for accurate reference extraction)
   - Citations
   - LaTeX equations
   - Author affiliations
   - Abstract
4. Results Integration: Combines all extracted data into a unified document representation

### Important Notes
- Anystyle is a critical component for reference extraction - DO NOT REMOVE OR REPLACE IT
- Marker should be used with its official Python API from marker.converters.pdf
- PDFs are preserved in the store directory until explicit deletion
- All text processing preserves semantic structure and layout
