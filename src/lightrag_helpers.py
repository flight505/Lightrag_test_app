import logging
import os
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from termcolor import colored

# Configure logging
logging.basicConfig(
    filename="lightrag.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ResponseProcessor:
    """Helper class for processing LightRAG responses and managing sources"""

    def __init__(self):
        """Initialize the response processor"""
        self.source_cache = {}

    def process_response(self, result: Dict[str, Any]) -> tuple[str, Any]:
        """Process the raw LightRAG response and extract key components

        Args:
            result: Raw response dictionary from LightRAG

        Returns:
            Tuple containing:
            - Processed response text
            - List of source references
        """
        try:
            response = result.get("response", "")
            logger.debug(f"Processed response: {response} (type: {type(response)})")
            return response, None

        except Exception as e:
            error_msg = f"Error processing response: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def format_sources(self, sources: List[str]) -> str:
        """Format source references into a readable string

        Args:
            sources: List of source references

        Returns:
            Formatted string of sources
        """
        try:
            if not sources:
                return "No sources available"

            formatted_sources = []
            for i, source in enumerate(sources, 1):
                formatted_sources.append(f"{i}. {source}")

            return "\n".join(formatted_sources)

        except Exception as e:
            error_msg = f"Error formatting sources: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def create_response_metadata(self, result: Dict) -> Dict:
        """Extract and format response metadata

        Args:
            result: Raw response dictionary from LightRAG

        Returns:
            Dictionary containing formatted metadata
        """
        try:
            metadata = {
                "processing_time": result.get("time", "N/A"),
                "token_usage": result.get("token_usage", "N/A"),
                "source_count": len(result.get("sources", [])),
                "timestamp": result.get("timestamp", "N/A"),
            }
            return metadata

        except Exception as e:
            error_msg = f"Error creating metadata: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def format_full_response(
        self, query: str, result: Dict[str, Any]
    ) -> str:
        """Create a fully formatted response with all components

        Args:
            query: Original query text
            result: Raw response dictionary from LightRAG

        Returns:
            Formatted response string
        """
        try:
            response = result.get("response", "No response available.")
            mode = result.get("mode", "Unknown")
            sources = result.get("sources", [])

            logger.debug(f"Formatting full response for query: {query}")
            formatted_sources = "\n".join([f"- {source}" for source in sources]) if sources else "No sources provided."

            return f"""
            ### Query:
            {query}

            ### Response:
            {response}

            ### Mode:
            {mode}

            ### Sources:
            {formatted_sources}
            """

        except Exception as e:
            error_msg = f"Error formatting full response: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def save_response_history(
        self, query: str, result: Dict, output_dir: str, filename: Optional[str] = None
    ) -> None:
        """Save response and metadata to disk

        Args:
            query: Original query text
            result: Raw response dictionary from LightRAG
            output_dir: Directory to save response
            filename: Optional custom filename
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Generate filename if not provided
            if not filename:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                filename = f"response_{timestamp}.txt"

            # Format full response
            formatted_response = self.format_full_response(query, result)

            # Save to file
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_response)

            print(colored(f"Response saved to {output_path}", "green"))

        except Exception as e:
            error_msg = f"Error saving response: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise

    def extract_key_points(self, response_text: str) -> List[str]:
        """Extract key points from response text

        Args:
            response_text: Raw response text

        Returns:
            List of key points
        """
        try:
            logger.debug("Extracting key points from response.")
            sentences = [s.strip() for s in response_text.split(".") if s.strip()]
            # Example: Extract the first 3 key points
            key_points = sentences[:3]
            logger.debug(f"Extracted key points: {key_points}")
            return key_points
        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            return []
