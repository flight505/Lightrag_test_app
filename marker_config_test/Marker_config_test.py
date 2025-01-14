"""Compare different Marker configurations for PDF conversion."""
import os
import time
from pathlib import Path
from termcolor import colored
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

# Input/output paths
PDF_PATH = '/Users/jesper/Documents/timeseries_papers/Che et al. - 2018 - Recurrent Neural Networks for Multivariate Time Series with Missing Values-annotated.pdf'
OUTPUT_DIR = Path(__file__).parent

def convert_with_config(config: dict, output_suffix: str):
    """Convert PDF using specified config and save to output path."""
    try:
        start_time = time.time()
        
        config_parser = ConfigParser(config)
        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer()
        )
        
        print(colored(f"\nConverting with {output_suffix} configuration...", "blue"))
        rendered = converter(PDF_PATH)
        
        output_path = OUTPUT_DIR / f"output_{output_suffix}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered.markdown)
            
        end_time = time.time()
        duration = round(end_time - start_time, 2)
            
        print(colored(f"✓ Saved output to {output_path}", "green"))
        print(colored(f"⏱ Time taken: {duration} seconds", "yellow"))
        
    except Exception as e:
        print(colored(f"Error during conversion: {str(e)}", "red"))

# Original config
original_config = {
    "output_format": "markdown",
    "layout_analysis": True,
    "detect_equations": True,
    "equation_detection_confidence": 0.3,
    "detect_inline_equations": True,
    "detect_tables": True,
    "detect_lists": True,
    "detect_code_blocks": True,
    "detect_footnotes": True,
    "equation_output": "latex",
    "preserve_math": True,
    "equation_detection_mode": "aggressive",
    "equation_context_window": 3,
    "equation_pattern_matching": True,
    "equation_symbol_extraction": True,
    
    "header_detection": {
        "enabled": True,
        "style": "atx",
        "levels": {
            "title": 1,
            "section": 2,
            "subsection": 3
        },
        "remove_duplicate_markers": True
    },
    
    "list_detection": {
        "enabled": True,
        "unordered_marker": "-",
        "ordered_marker": "1.",
        "preserve_numbers": True,
        "indent_spaces": 2
    },
    
    "layout": {
        "paragraph_breaks": True,
        "line_spacing": 2,
        "remove_redundant_whitespace": True,
        "preserve_line_breaks": True,
        "preserve_blank_lines": True
    },
    
    "preserve": {
        "links": True,
        "tables": True,
        "images": True,
        "footnotes": True,
        "formatting": True,
        "lists": True,
        "headers": True
    },
    
    "output": {
        "format": "markdown",
        "save_markdown": True,
        "save_text": True,
        "markdown_ext": ".md",
        "text_ext": ".txt"
    }
}

# Enhanced config for better citation handling
enhanced_config = {
    # Core settings
    "output_format": "markdown",
    "debug": True,
    "force_ocr": False,
    "strip_existing_ocr": True,
    
    # Layout analysis
    "layout_analysis": True,
    "detect_equations": True,
    "detect_tables": True,
    "detect_lists": True,
    "detect_footnotes": True,
    "detect_inline_equations": True,
    "equation_output": "latex",
    "preserve_math": True,
    "equation_detection_mode": "aggressive",
    "equation_context_window": 3,
    "equation_pattern_matching": True,
    "equation_symbol_extraction": True,
    
    # Citation and reference handling
    "layout": {
        "paragraph_breaks": True,
        "line_spacing": 1,
        "remove_redundant_whitespace": True,
        "preserve_line_breaks": False,
        "preserve_blank_lines": True
    },
    
    # Content detection
    "metadata": {
        "extract_title": True,
        "extract_authors": True,
        "extract_abstract": True,
        "extract_references": True,
        "extract_citations": True,
        "table_of_contents": True
    },
    
    # Debug settings
    "debug_pdf_images": True,
    "debug_layout_images": True,
    
    # Output settings
    "output": {
        "format": "markdown",
        "save_markdown": True,
        "save_text": True,
        "save_debug": True
    }
}

if __name__ == "__main__":
    print(colored("Starting PDF conversion comparison...", "blue"))
    
    # Convert with both configs
    convert_with_config(original_config, "original")
    convert_with_config(enhanced_config, "enhanced")
    
    print(colored("\nConversion complete! Compare outputs in:", "green"))
    print(colored("- output_original.md", "white"))
    print(colored("- output_enhanced.md", "white"))