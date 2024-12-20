import os
import logging
from transformers import AutoProcessor, AutoModelForVision2Seq
from pdfminer.high_level import extract_text
from termcolor import colored

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
DEVICE = "mps"  # Use Metal Performance Shaders for Apple Silicon
MODEL_NAME = "HuggingFaceM4/idefics2-8b"

def convert_pdf_to_text(pdf_path):
    if not os.path.exists(pdf_path):
        logging.error(f"File not found: {pdf_path}")
        return None

    try:
        logging.info(f"Extracting text from {pdf_path}...")
        text = extract_text(pdf_path)
        logging.info("Extraction complete.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text: {e}")
        return None

def main():
    # Load the model
    try:
        processor = AutoProcessor.from_pretrained(MODEL_NAME)
        model = AutoModelForVision2Seq.from_pretrained(MODEL_NAME).to(DEVICE)
        logging.info("Model loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        return

    # Example PDF file
    pdf_path = "Deep-learning-based.pdf"
    text = convert_pdf_to_text(pdf_path)

    if text:
        # Process the text with Idefics2 if needed
        logging.info("Processing text with Idefics2...")
        # ... additional processing ...

        # Save to a .txt file
        output_path = "output.txt"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            logging.info(f"Text saved to {output_path}")
        except Exception as e:
            logging.error(f"Error saving text: {e}")

if __name__ == "__main__":
    main()
