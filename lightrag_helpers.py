import logging
import os
from typing import Dict, List, Optional, Tuple

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

    def process_response(self, result: Dict) -> Tuple[str, List[str]]:
        """Process the raw LightRAG response and extract key components

        Args:
            result: Raw response dictionary from LightRAG

        Returns:
            Tuple containing:
            - Processed response text
            - List of source references
        """
        try:
            response_text = result.get("response", "No response generated")
            sources = result.get("sources", [])

            return response_text, sources

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
        self, query: str, result: Dict, include_metadata: bool = True
    ) -> str:
        """Create a fully formatted response with all components

        Args:
            query: Original query text
            result: Raw response dictionary from LightRAG
            include_metadata: Whether to include processing metadata

        Returns:
            Formatted response string
        """
        try:
            # Process response components
            response_text, sources = self.process_response(result)
            formatted_sources = self.format_sources(sources)

            # Build response string
            formatted_response = [
                f"**Query:**\n{query}\n",
                f"**Response:**\n{response_text}\n",
                f"**Sources:**\n{formatted_sources}\n",
            ]

            # Add metadata if requested
            if include_metadata:
                metadata = self.create_response_metadata(result)
                metadata_str = "\n".join(f"- {k}: {v}" for k, v in metadata.items())
                formatted_response.append(f"**Metadata:**\n{metadata_str}")

            return "\n".join(formatted_response)

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
            # Split text into sentences and filter for key points
            sentences = [s.strip() for s in response_text.split(".") if s.strip()]
            key_points = []

            for sentence in sentences:
                # Add logic to identify key points (can be customized)
                if len(sentence.split()) > 5:  # Simple length-based filter
                    key_points.append(f"- {sentence}")

            return key_points if key_points else ["No key points identified"]

        except Exception as e:
            error_msg = f"Error extracting key points: {str(e)}"
            print(colored(error_msg, "red"))
            logger.error(error_msg)
            raise
