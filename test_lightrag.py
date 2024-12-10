import logging
import os
from typing import Union

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete
from lightrag.utils import EmbeddingFunc
from termcolor import colored

# Define major constants
WORKING_DIR = "./test_rag"
TEST_FILE = "./test_data.txt"

TEST_CONTENT = """
LightRAG is a powerful RAG (Retrieval-Augmented Generation) system that combines:
1. Local and global search capabilities
2. Knowledge graph integration
3. Vector database functionality
4. Multiple query modes including naive, local, global, and hybrid searches

It supports various LLM models and can be used for both simple and complex document analysis tasks.
"""


def setup_test_environment():
    """Set up the test environment with necessary directories and files"""
    try:
        # Create working directory if it doesn't exist
        if not os.path.exists(WORKING_DIR):
            os.makedirs(WORKING_DIR)
            print(colored("Created working directory", "green"))

        # Create test file
        with open(TEST_FILE, "w", encoding="utf-8") as f:
            f.write(TEST_CONTENT)
            print(colored("Created test file", "green"))

    except Exception as e:
        print(colored(f"Error in setup: {str(e)}", "red"))
        raise


def test_lightrag():
    """Test basic LightRAG functionality with default NetworkX storage"""
    try:
        # Initialize LightRAG with default storage options
        rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=gpt_4o_mini_complete,
            log_level="DEBUG",
        )
        print(colored("LightRAG initialized successfully", "green"))

        # Insert test content
        with open(TEST_FILE, "r", encoding="utf-8") as f:
            rag.insert(f.read())
        print(colored("Content inserted successfully", "green"))

        # Test different query modes
        test_query = "What are the main features of LightRAG?"
        modes = ["naive", "local", "global", "hybrid"]

        for mode in modes:
            try:
                print(colored(f"\nTesting {mode} mode:", "cyan"))
                result = rag.query(test_query, param=QueryParam(mode=mode))
                print(colored("Query result:", "yellow"))
                print(result)
            except Exception as e:
                print(colored(f"Error in {mode} mode query: {str(e)}", "red"))

    except Exception as e:
        print(colored(f"Error in test: {str(e)}", "red"))
        raise


def cleanup():
    """Clean up test files and directories"""
    try:
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
        if os.path.exists(WORKING_DIR):
            import shutil

            shutil.rmtree(WORKING_DIR)
        print(colored("Cleanup completed", "green"))
    except Exception as e:
        print(colored(f"Error in cleanup: {str(e)}", "red"))


def main():
    try:
        print(colored("Starting LightRAG test...", "cyan"))
        setup_test_environment()
        test_lightrag()
        cleanup()
        print(colored("Test completed successfully!", "green"))
    except Exception as e:
        print(colored(f"Test failed: {str(e)}", "red"))
        cleanup()
        raise


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    main()
