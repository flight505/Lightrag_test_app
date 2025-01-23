# LightRAG CLI Development Guide

## Table of Contents
1. [Project Objective](#1-project-objective)
2. [Pre-Development Analysis](#2-pre-development-analysis)
3. [Core Functionality](#3-core-functionality)
4. [Development Process](#4-development-process)
5. [Implementation Guide](#5-implementation-guide)
6. [Testing Strategy](#6-testing-strategy)
7. [Best Practices & Common Pitfalls](#7-best-practices--common-pitfalls)
8. [Code Examples](#8-code-examples)
9. [Migration Checklist](#9-migration-checklist)
10. [Framework Separation Strategy](#10-framework-separation-strategy)
11. [Performance Considerations](#11-performance-considerations)
12. [Command Implementation Examples](#12-command-implementation-examples)

## 1. Project Objective

### 1.1 Overview
Transform LightRAG from a web application into a focused command-line interface (CLI) application, creating a clean, well-structured project.

### 1.2 Key Goals
1. **Core Functionality**: Preserve essential academic paper processing:
   - PDF text extraction (Marker)
   - DOI/arXiv identification (pdf2doi)
   - Metadata fetching (CrossRef/arXiv APIs)
   - Reference extraction (Anystyle)
   - Equation metadata processing
   - Knowledge graph capabilities

2. **Architecture**:
   - Remove all web framework dependencies
   - Simplify state management
   - Create modular CLI structure
   - Implement clear separation of concerns

3. **User Experience**:
   - Intuitive command-line interface (Click)
   - Rich console output formatting
   - Progress indicators for long operations
   - Clear error messages

4. **Quality**:
   - Basic test coverage to help identify issues and guide development
   - Proper error handling
   - Python best practices
   - Code maintainability

## 2. Pre-Development Analysis

### 2.1 Critical Dependencies
1. **Framework Dependencies to Remove**:
   ```python
   import streamlit
   @st.cache_data
   st.session_state
   st.progress()
   ```

2. **Core Processing Chain to Preserve**:
   ```
   PDF -> pdf2doi -> DOI/arXiv ID -> CrossRef/arXiv API -> Metadata -> Anystyle -> Raw References
   ```

### 2.2 Critical Test Files
- `tests/test_citation_processor.py`
- `tests/test_metadata.py`

### 2.3 Critical Rules
1. **DO NOT**:
   - Modify working PDF processing pipeline
   - Change store structure
   - Remove error handling
   - Modify test assertions

2. **DO**:
   - Read test files first
   - Preserve metadata extraction
   - Maintain processing chain
   - Keep equation/citation extraction
   - Check the real-time project monitoring file periodically to see current progress and file status, the file is `Focus.md`

## 3. Core Functionality

### 3.1 Required Final Directory Structure
```
store/
├── documents/     # Original PDFs
├── metadata/      # Extracted metadata
├── converted/     # Converted text
├── cache/         # Processing cache
└── exports/       # Generated exports
```

### 3.2 Required Files
1. **Metadata Files**:
   - `metadata.json`
   - `consolidated.json`

### 3.3 Processing Pipeline
1. PDF Text Extraction
2. Identifier Detection
3. Metadata Retrieval
4. Reference Processing
5. Equation Analysis

## 4. Development Process

### 4.1 Initial Setup
1. Remove web-specific files:
   ```bash
   rm -rf pages/
   rm streamlit_app.py
   ```

2. Clean source files:
   ```python
   # Remove Streamlit caching
   @lru_cache(maxsize=32)
   def process_file(self):
       pass
   ```

### 4.2 Implementation Order
1. **Phase 1: Core Cleanup**
   - Remove web dependencies
   - Simplify state management
   - Create base classes

2. **Phase 2: CLI Foundation**
   - Basic store operations
   - Document processing
   - Search functionality

3. **Phase 3: Features**
   - Citation graph
   - Equation search
   - Knowledge graph

4. **Phase 4: Polish**
   - Error handling
   - Progress reporting
   - Documentation

## 5. Implementation Guide

### 5.1 Project Structure
```
cli/
├── __init__.py
├── main.py           # Entry point
└── commands/         # Command modules
    ├── pdf.py       # PDF processing
    ├── store.py     # Store management
    ├── search.py    # Search functionality
    └── metadata.py  # Metadata operations
```

### 5.2 Command Implementation
1. **Store Commands** (First)
   - Create/delete stores
   - List contents
   - Validate structure

2. **PDF Commands** (Second)
   - Process documents
   - Extract metadata
   - Convert formats

3. **Search Commands** (Third)
   - Query documents
   - Generate graphs
   - Analyze content

### 5.3 Progress Handling
```python
def process_file(self, file_path: str, 
                progress_callback: Optional[Callable] = None):
    try:
        if progress_callback:
            progress_callback(0, 100)
        # Processing steps...
        if progress_callback:
            progress_callback(100, 100)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
```

## 6. Testing Strategy

### 6.1 Test Structure
```
tests/
├── conftest.py      # Shared fixtures
├── test_processor.py
└── cli/
    ├── test_pdf.py
    ├── test_store.py
    └── test_search.py
```

### 6.2 Test Implementation
```python
def test_process_command(runner):
    """Test basic PDF processing."""
    result = runner.invoke(cli, [
        'pdf', 'process', 
        'tests/pdfs/sample.pdf', 
        'test_store'
    ])
    assert result.exit_code == 0
    assert "Processing complete" in result.output
```

### 6.3 Test Fixtures
```python
@pytest.fixture
def test_env(tmp_path):
    """Setup test environment."""
    # Setup store
    store_path = setup_test_store(tmp_path)
    
    # Copy test files
    test_files = setup_test_files(tmp_path)
    
    yield {
        "store_path": store_path,
        "test_files": test_files
    }
    
    # Cleanup
    cleanup_test_env(tmp_path)
```

## 7. Best Practices & Common Pitfalls

### 7.1 Store Management
- **Problem**: Store validation fails
- **Solution**:
  ```python
  def create_store(name: str):
      store_path = Path(name)
      # Create ALL directories first
      for dir_name in ["documents", "metadata", 
                      "converted", "cache"]:
          (store_path / dir_name).mkdir(
              parents=True, exist_ok=True
          )
      # Initialize metadata files
      init_metadata_files(store_path)
  ```

### 7.2 Error Handling
- **Problem**: Silent failures
- **Solution**:
  ```python
  def process_pdf(file_path: str):
      # 1. Validate file
      if not Path(file_path).exists():
          raise FileNotFoundError(
              f"PDF not found: {file_path}"
          )
      
      # 2. Validate store
      if not validate_store_structure(store_path):
          raise ValueError("Invalid store structure")
      
      # 3. Process with error handling
      try:
          result = process_with_marker(file_path)
          if not result:
              raise ProcessingError("No text extracted")
      except Exception as e:
          raise ProcessingError(
              f"Processing failed: {str(e)}"
          )
  ```

## 8. Code Examples

### 8.1 Command Group Example
```python
@click.group()
def pdf():
    """PDF processing commands."""
    pass

@pdf.command()
@click.argument('file')
@click.argument('store')
def process(file: str, store: str):
    """Process a PDF file."""
    try:
        processor = DocumentProcessor()
        result = processor.process_file(Path(file))
        console.print("✓ Processing complete", 
                     style="green")
    except Exception as e:
        console.print(f"Error: {str(e)}", 
                     style="red")
        raise click.Abort()
```

### 8.2 Search Implementation
```python
@search.command()
@click.argument('query')
@click.argument('store')
@click.option('--mode', 
             type=click.Choice(
                 ['mix', 'hybrid', 'local', 'global']
             ), 
             default='mix')
def query(query: str, store: str, mode: str):
    """Search documents in store."""
    try:
        results = search_documents(
            query, store, mode=mode
        )
        display_results(results)
    except Exception as e:
        handle_error(e)
        raise click.Abort()
```

## 9. Migration Checklist

### 9.1 Before Starting
- [ ] Backup codebase
- [ ] Document core functionality
- [ ] Map web dependencies
- [ ] List CLI commands

### 9.2 During Migration
- [ ] Remove web files systematically
- [ ] Test after each removal
- [ ] Track broken dependencies
- [ ] Document API changes

### 9.3 After Migration
- [ ] Verify core functionality
- [ ] Run all tests
- [ ] Check CLI commands
- [ ] Update docs 

## 10. Framework Separation Strategy

### 10.1 Immediate File Processor Separation
```python
# CURRENT (problematic):
# src/file_processor.py
import streamlit as st

class FileProcessor:
    @st.cache_data
    def process_file(self, file_path: str):
        pass

# CORRECT SEPARATION:
# src/processing/pdf.py
from functools import lru_cache

class PDFProcessor:
    @lru_cache
    def process_file(self, file_path: str):
        pass

# web/components/processor.py
import streamlit as st
from src.processing.pdf import PDFProcessor

class WebPDFProcessor(PDFProcessor):
    @st.cache_data
    def process_file(self, file_path: str):
        return super().process_file(file_path)
```

### 10.2 Progress Handling Separation
```python
# src/processing/base.py
from typing import Protocol
from pathlib import Path

class ProgressCallback(Protocol):
    def update(self, current: int, total: int): ...

class BaseProcessor:
    def __init__(self, progress_callback: Optional[ProgressCallback] = None):
        self.progress_callback = progress_callback

    def process_file(self, file_path: Path):
        if self.progress_callback:
            self.progress_callback.update(1, 100)
```

### 10.3 Error Handling Hierarchy
```python
class LightRAGError(Exception):
    """Base exception for all LightRAG errors"""
    pass

class PDFProcessingError(LightRAGError):
    """PDF processing specific errors"""
    pass

class MetadataError(LightRAGError):
    """Metadata handling errors"""
    pass

def handle_error(error: LightRAGError):
    error_styles = {
        PDFProcessingError: "red bold",
        MetadataError: "yellow bold",
        LightRAGError: "red"
    }
    style = error_styles.get(type(error), "red")
    console.print(f"Error: {str(error)}", style=style)
```

## 11. Performance Considerations

### 11.1 Caching Strategy
1. Use `lru_cache` for expensive operations:
```python
from functools import lru_cache

class DocumentProcessor:
    @lru_cache(maxsize=32)
    def process_document(self, file_path: str) -> Dict[str, Any]:
        # Expensive document processing
        pass
```

2. Cache API responses:
```python
class APICache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get_cached_response(self, key: str) -> Optional[Dict]:
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None

    def cache_response(self, key: str, data: Dict):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps(data))
```

### 11.2 Memory Management
1. Process large PDFs in chunks:
```python
def process_large_pdf(file_path: str, chunk_size: int = 1000):
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            process_chunk(chunk)
            yield len(chunk)
```

2. Use generators for large datasets:
```python
def search_documents(query: str, store_path: Path):
    for doc_path in store_path.glob('**/*.pdf'):
        if match := search_single_doc(doc_path, query):
            yield match
```

## 12. Command Implementation Examples

### 12.1 Store Commands
```python
@click.group()
def store():
    """Store management commands."""
    pass

@store.command()
@click.argument('name')
def create(name: str):
    """Create a new document store."""
    try:
        manager = StoreManager()
        store_path = manager.create_store(name)
        console.print(f"✓ Created store: {name}", style="green")
        console.print(f"Location: {store_path}", style="blue")
    except Exception as e:
        handle_error(e)
        raise click.Abort()

@store.command()
@click.argument('name')
def delete(name: str):
    """Delete a document store."""
    try:
        if not click.confirm(f"Delete store '{name}'?"):
            return
        manager = StoreManager()
        manager.delete_store(name)
        console.print(f"✓ Deleted store: {name}", style="green")
    except Exception as e:
        handle_error(e)
        raise click.Abort()
```

### 12.2 PDF Commands
```python
@click.group()
def pdf():
    """PDF processing commands."""
    pass

@pdf.command()
@click.argument('file')
@click.argument('store')
@click.option('--engine', 
             type=click.Choice(['auto', 'marker', 'pymupdf', 'pypdf2']),
             default='marker',
             help="PDF processing engine to use")
def process(file: str, store: str, engine: str):
    """Process a PDF file."""
    try:
        processor = DocumentProcessor(engine=engine)
        with Progress() as progress:
            task = progress.add_task("Processing", total=100)
            
            # Validate inputs
            if not Path(file).exists():
                raise PDFProcessingError(f"PDF not found: {file}")
            
            # Process with progress
            result = processor.process_file(
                Path(file),
                lambda current, total: progress.update(
                    task,
                    completed=int(current/total * 100)
                )
            )
            
            # Show results
            console.print("\nProcessing Results:", style="bold blue")
            console.print(f"Title: {result.title}")
            console.print(f"Authors: {', '.join(result.authors)}")
            console.print(f"References: {len(result.references)}")
            
    except Exception as e:
        handle_error(e)
        raise click.Abort()
```

### 12.3 Search Commands
```python
@click.group()
def search():
    """Search and query commands."""
    pass

@search.command()
@click.argument('query')
@click.argument('store')
@click.option('--mode', 
             type=click.Choice(['mix', 'hybrid', 'local', 'global']),
             default='mix')
def query(query: str, store: str, mode: str):
    """Search documents in store."""
    try:
        # Initialize search
        manager = SearchManager(store)
        
        # Execute search with progress
        with Progress() as progress:
            task = progress.add_task("Searching...", total=100)
            
            results = manager.search(
                query, 
                mode=mode,
                progress_callback=lambda c, t: progress.update(
                    task,
                    completed=int(c/t * 100)
                )
            )
        
        # Display results
        if not results:
            console.print("No results found", style="yellow")
            return
            
        table = Table(show_header=True)
        table.add_column("Document")
        table.add_column("Score")
        table.add_column("Context")
        
        for result in results:
            table.add_row(
                result.document_name,
                f"{result.score:.2f}",
                result.context[:100] + "..."
            )
        
        console.print(table)
        
    except Exception as e:
        handle_error(e)
        raise click.Abort()
```

### 12.4 Metadata Commands
```python
@click.group()
def metadata():
    """Metadata management commands."""
    pass

@metadata.command()
@click.argument('store')
def consolidate(store: str):
    """Consolidate metadata in store."""
    try:
        consolidator = MetadataConsolidator(store)
        
        with Progress() as progress:
            task = progress.add_task("Consolidating", total=100)
            
            # Process metadata
            result = consolidator.consolidate(
                progress_callback=lambda c, t: progress.update(
                    task,
                    completed=int(c/t * 100)
                )
            )
        
        # Show results
        console.print("\nConsolidation Results:", style="bold blue")
        console.print(f"Documents processed: {result.total_docs}")
        console.print(f"Citations found: {result.total_citations}")
        console.print(f"Equations extracted: {result.total_equations}")
        
    except Exception as e:
        handle_error(e)
        raise click.Abort()
``` 