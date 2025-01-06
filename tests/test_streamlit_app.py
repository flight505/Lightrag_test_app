import streamlit as st
from streamlit.testing.v1 import AppTest
import os
from pathlib import Path
import json
from termcolor import colored
import time
from unittest.mock import MagicMock, patch
from src.academic_metadata import MetadataExtractor
from src.config_manager import ConfigManager

# Mock MetadataExtractor before importing app
mock_extractor = MagicMock(spec=MetadataExtractor)
mock_config = MagicMock(spec=ConfigManager)

# Mock the entire app initialization
with patch('src.academic_metadata.MetadataExtractor') as mock_extractor_class, \
     patch('streamlit.sidebar.checkbox') as mock_checkbox:
    mock_extractor_class.return_value = mock_extractor
    mock_checkbox.return_value = False
    
    def test_pdf_processing():
        """Test PDF processing through the Streamlit app interface"""
        # Initialize app test
        at = AppTest.from_file("streamlit_app.py")
        
        # Initialize session state
        at.session_state["initialized"] = False
        at.session_state["active_store"] = None
        at.session_state["status_ready"] = False
        at.session_state["config_manager"] = mock_config
        at.run()
        
        # Wait for app to be ready
        time.sleep(2)
        
        # Click "Go to Document Manager" button from home page
        buttons = at.main.button
        for button in buttons:
            if button.label == "Go to Document Manager":
                button.click()
                break
        at.run()
        
        # Wait for page to load
        time.sleep(1)
        
        # Create a new store
        inputs = at.main.text_input
        for input in inputs:
            if input.label == "Store Name":
                input.set_value("test_store")
                break
        
        buttons = at.main.button
        for button in buttons:
            if button.label == "Create Store":
                button.click()
                break
        at.run()
        
        # Wait for store to be created
        time.sleep(1)
        
        # Check if store was created
        selects = at.main.selectbox
        for select in selects:
            if select.label == "Select Document Store":
                assert "test_store" in select.options
                break
        
        # Process test PDF
        test_pdf = "pdfs/Pharmacokinetic–pharmacodynamic modeling of maintenance therapy for childhood acute lymphoblastic leukemia.pdf"
        assert os.path.exists(test_pdf), "Test PDF not found"
        
        # Click convert pending button
        buttons = at.main.button
        for button in buttons:
            if button.label == "⚡ Convert Pending":
                button.click()
                break
        at.run()
        
        # Wait for processing to complete
        time.sleep(5)
        
        # Check metadata file
        metadata_path = os.path.splitext(test_pdf)[0] + '.metadata.json'
        assert os.path.exists(metadata_path), "Metadata file not created"
        
        # Verify metadata content
        with open(metadata_path, encoding='utf-8') as f:
            metadata = json.load(f)
            print(colored("\nMetadata verification:", "blue"))
            print(f"✓ Title: {metadata.get('title', 'N/A')}")
            print(f"✓ References found: {len(metadata.get('references', []))}")
            print(f"✓ Citations found: {len(metadata.get('citations', []))}")
            print(f"✓ Equations found: {len(metadata.get('equations', []))}")
            
            # Verify citations have references linked
            citations = metadata.get('citations', [])
            if citations:
                print("\nSample citation verification:")
                for cit in citations[:2]:
                    print(f"- Citation: {cit['text']}")
                    print(f"  Context: {cit.get('context', 'N/A')}")
                    if cit.get('references'):
                        print(f"  Linked references: {len(cit['references'])}")
                        for ref in cit['references'][:2]:
                            print(f"    - {ref}")
            
            # Basic assertions
            assert metadata.get('title'), "Title not extracted"
            assert len(metadata.get('references', [])) > 0, "No references extracted"
            assert len(metadata.get('citations', [])) > 0, "No citations extracted"

    if __name__ == "__main__":
        test_pdf_processing() 