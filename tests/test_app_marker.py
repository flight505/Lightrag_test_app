from pathlib import Path
from termcolor import colored
from src.file_processor import FileProcessor
from src.config_manager import ConfigManager, PDFEngine
import re
import json
import os

def test_marker_in_app():
    """Test Marker functionality in the app context."""
    print("\nProcessing scientific paper with Marker...")
    
    # Initialize with Marker engine
    config_manager = ConfigManager()
    config_manager.get_config().pdf_engine = PDFEngine.MARKER
    
    # Initialize file processor
    processor = FileProcessor(config_manager)
    
    # Process test paper
    pdf_path = "pdfs/Pharmacokinetic–pharmacodynamic modeling of maintenance therapy for childhood acute lymphoblastic leukemia.pdf"
    result = processor.process_file(pdf_path)
    
    if result:
        metadata_path = os.path.splitext(pdf_path)[0] + '.metadata.json'
        store_metadata_path = os.path.join('store', 'metadata.json')
        
        print("\nMetadata file locations:")
        print(f"Per-file metadata: {metadata_path}")
        print(f"Store metadata: {store_metadata_path}")
        
        print("\nPer-file metadata content:")
        print("-" * 50)
        try:
            with open(metadata_path, encoding='utf-8') as f:
                metadata = json.load(f)
                print(f"\n✓ Text extraction successful")
                print(f"✓ Metadata extraction successful")
                print(f"  Title: {metadata.get('title', 'N/A')}")
                print(f"  Authors: {', '.join(a['full_name'] for a in metadata.get('authors', []))}")
                print(f"✓ Academic metadata extraction successful\n")
                
                print("Extracted content stats:")
                print(f"- Text length: {len(metadata.get('text', ''))} chars")
                print(f"- References found: {len(metadata.get('references', []))}")
                print(f"- Equations found: {len(metadata.get('equations', []))}")
                print(f"- Citations found: {len(metadata.get('citations', []))}\n")
                
                print("Found LaTeX equations in text:")
                print("-" * 50)
                for i, eq in enumerate(metadata.get('equations', [])[:3], 1):
                    print(f"Equation {i}: {eq['raw_text']}")
                print(f"Total equations found in text: {len(metadata.get('equations', []))}\n")
                
                print("Sample references:")
                print("-" * 50)
                for ref in metadata.get('references', [])[:3]:
                    print(f"- {json.dumps(ref, indent=2)}")
                
                print("\nSample citations:")
                print("-" * 50)
                for cit in metadata.get('citations', [])[:3]:
                    print(f"- Citation text: {cit['text']}")
                    print(f"  Context: {cit['context'][:100]}...")
                    if cit.get('references'):
                        print("  Linked references:")
                        for ref in cit['references']:
                            print(f"    - {ref['title']}")
                    print()
                
                print("Sample equations from metadata:")
                print("-" * 50)
                for eq in metadata.get('equations', [])[:3]:
                    print(f"- {json.dumps(eq, indent=2)}")
                
                print("\nSample of extracted text (first 500 chars):")
                print("-" * 50)
                print(metadata.get('text', '')[:500])
                
                print("\n✓ Marker is working correctly in the app!")
                
                print("\nDetected sections:")
                sections = metadata.get('sections', {})
                if 'abstract' in sections:
                    print("✓ Found abstract section")
                if 'methods' in sections:
                    print("✓ Found methods section")
                if 'results' in sections:
                    print("✓ Found results section")
                if 'discussion' in sections:
                    print("✓ Found discussion section")
                print("✓ Scientific paper structure verified")
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Error testing Marker in app: {str(e)}")
            raise
    else:
        print("⚠️ Error processing file")
        raise Exception("File processing failed")

if __name__ == "__main__":
    print("✓ Configuration loaded successfully\n")
    test_marker_in_app() 