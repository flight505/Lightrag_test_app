# LightRAG Refactoring Guide

## Key Issues Identified

### 1. Framework Dependencies
- Streamlit dependencies scattered throughout core logic
- Web-specific state management in processing chain
- UI-coupled progress reporting
- Framework-specific caching decorators

### 2. Code Organization
- Mixed concerns in `file_processor.py` (629 lines)
- Duplicate logic between CLI and web implementations
- Complex configuration management
- Inconsistent error handling patterns

### 3. Processing Pipeline
- Tightly coupled with web framework
- Complex state management
- Inefficient progress reporting
- Redundant API calls

## Recommended Solutions

### 1. Core Architecture Cleanup
```python
# BEFORE (src/file_processor.py):
class FileProcessor:
    @st.cache_data
    def process_file(self, file_path: str):
        with st.progress("Processing..."):
            # Processing logic

# AFTER (src/processing/document.py):
class DocumentProcessor:
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        
    def process_file(self, file_path: Path) -> ProcessingResult:
        """Process a document with optional progress reporting."""
        try:
            if self.progress_callback:
                self.progress_callback(0, "Starting processing")
                
            # Core processing logic
            
            if self.progress_callback:
                self.progress_callback(100, "Processing complete")
                
            return ProcessingResult(...)
            
        except Exception as e:
            raise ProcessingError(f"Processing failed: {str(e)}")
```

### 2. Store Management Simplification
```python
# src/store/store.py
class Store:
    """Clean, framework-agnostic store management."""
    
    def __init__(self, root_path: Path):
        self.root = root_path
        
    def create(self, name: str) -> Path:
        """Create a new document store."""
        store_path = self.root / name
        self._create_structure(store_path)
        return store_path
        
    def _create_structure(self, path: Path):
        """Create standard store structure."""
        for dir_name in ["documents", "metadata", "converted", "cache", "exports"]:
            (path / dir_name).mkdir(parents=True, exist_ok=True)
```

### 3. Search Implementation
```python
# src/search/search.py
class Search:
    """Framework-agnostic search functionality."""
    
    def __init__(self, store_path: Path):
        self.store_path = store_path
        
    def query(self, query: str, mode: str = "mix") -> List[SearchResult]:
        """Execute search query."""
        try:
            # Core search logic
            return results
        except Exception as e:
            raise SearchError(f"Search failed: {str(e)}")
```

## Implementation Priority

1. **Core Cleanup (High Priority)**
   - Remove framework dependencies
   - Implement clean base classes
   - Separate configuration management
   - Standardize error handling

2. **Testing Infrastructure (High Priority)**
   - Implement framework-agnostic test fixtures
   - Add CLI-specific test cases
   - Create integration tests
   - Ensure backward compatibility

3. **Interface Layer (Medium Priority)**
   - Implement CLI commands
   - Add progress reporting
   - Enhance error presentation
   - Create help documentation

4. **Documentation (Medium Priority)**
   - Update API documentation
   - Create CLI usage guide
   - Document test patterns
   - Add example workflows

5. **Code Improvements (Low Priority)**
   - Optimize performance
   - Enhance error messages
   - Add debug logging
   - Improve code comments

## Specific Code Improvements

### 1. Error Handling
```python
class LightRAGError(Exception):
    """Base exception for all LightRAG errors."""
    pass

class ProcessingError(LightRAGError):
    """Document processing errors."""
    pass

class StoreError(LightRAGError):
    """Store management errors."""
    pass

def handle_error(error: LightRAGError):
    """Framework-agnostic error handling."""
    error_map = {
        ProcessingError: ("Processing failed", "red"),
        StoreError: ("Store operation failed", "yellow"),
    }
    msg, color = error_map.get(type(error), ("Operation failed", "red"))
    return msg, str(error), color
```

### 2. Progress Reporting
```python
from typing import Protocol, Optional

class ProgressReporter(Protocol):
    """Framework-agnostic progress reporting."""
    def update(self, percentage: int, message: str): ...

class Processor:
    def __init__(self, progress: Optional[ProgressReporter] = None):
        self.progress = progress
        
    def report_progress(self, percentage: int, message: str):
        """Report progress if handler is available."""
        if self.progress:
            self.progress.update(percentage, message)
```

### 3. Configuration Management
```python
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class ProcessingConfig(BaseModel):
    """Clean configuration management."""
    store_root: Path
    cache_dir: Optional[Path] = None
    pdf_engine: str = "marker"
    max_workers: int = 4
```

## Lessons Learned

1. **Test-First Development**
   - Write tests before implementing features
   - Use test failures to guide development
   - Maintain test coverage during refactoring

2. **Clean Architecture**
   - Keep core logic framework-agnostic
   - Use dependency injection for flexibility
   - Implement clear interfaces

3. **Code Organization**
   - Small, focused classes and functions
   - Clear separation of concerns
   - Consistent error handling
   - Framework-agnostic core

4. **Error Handling**
   - Use custom exception hierarchy
   - Provide detailed error messages
   - Implement proper cleanup
   - Log errors appropriately

## Next Steps

1. **Create New Branch**
   ```bash
   git checkout -b refactor/cli-only
   ```

2. **Remove Web Dependencies**
   ```bash
   rm -rf pages/
   rm streamlit_app.py
   ```

3. **Update Dependencies**
   ```toml
   # pyproject.toml
   [tool.poetry.dependencies]
   python = "^3.10"
   click = "^8.1.7"
   rich = "^13.7.0"
   # Remove streamlit and related packages
   ```

4. **Implement Core Changes**
   - Create new core classes
   - Update test suite
   - Add CLI commands
   - Update documentation

## Success Metrics

1. **Code Quality**
   - No framework dependencies in core code
   - Comprehensive test coverage
   - Clear error messages
   - Proper progress reporting

2. **Functionality**
   - All features working via CLI
   - Proper error handling
   - Efficient processing
   - Clear user feedback

3. **Documentation**
   - Updated API documentation
   - CLI usage guide
   - Example workflows
   - Clear error solutions
