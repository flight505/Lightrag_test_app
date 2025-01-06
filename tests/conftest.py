import pytest
import os
import tempfile
from pathlib import Path

@pytest.fixture(scope="session")
def test_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test"""
    env_vars = [
        "PDF_ENGINE",
        "ENABLE_CROSSREF",
        "ENABLE_SCHOLARLY",
        "DEBUG_MODE",
        "MAX_FILE_SIZE_MB",
        "TIMEOUT_SECONDS"
    ]
    
    # Store original values
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]

@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing"""
    return """
    Title: Test Document
    Author: John Doe
    
    Abstract:
    This is a test document for unit testing.
    
    Introduction:
    Lorem ipsum dolor sit amet.
    
    References:
    1. Smith, J. (2020). Test paper.
    2. Doe, J. (2021). Another paper.
    """ 