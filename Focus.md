# Project Focus: Lightrag_test_app

**Current Goal:** Project directory structure and information

**Project Context:**
Type: Language: python
Target Users: Users of Lightrag_test_app
Main Functionality: Project directory structure and information
Key Requirements:
- Type: Python Project
- Language: python
- Framework: none
- File and directory tracking
- Automatic updates

**Development Guidelines:**
- Keep code modular and reusable
- Follow best practices for the project type
- Maintain clean separation of concerns

# 📁 Project Structure
├─ 📄 streamlit_app.py (79 lines) - Python script containing project logic
├─ 📁 cli
│  ├─ 📄 __init__.py (1 lines) - Python script containing project logic
│  ├─ 📄 main.py (37 lines) - Python script containing project logic
│  ├─ 📁 commands
│  │  ├─ 📄 __init__.py (1 lines) - Python script containing project logic
│  │  ├─ 📄 pdf_cmd.py (159 lines) - Python script containing project logic
│  │  ├─ 📄 search_cmd.py (194 lines) - Python script containing project logic
│  │  └─ 📄 store_cmd.py (115 lines) - Python script containing project logic
│  └─ 📁 core
│     ├─ 📄 __init__.py (1 lines) - Python script containing project logic
│     ├─ 📄 config.py (89 lines) - Python script containing project logic
│     ├─ 📄 errors.py (40 lines) - Python script containing project logic
│     ├─ 📄 progress.py (33 lines) - Python script containing project logic
│     └─ 📄 store_manager.py (229 lines) - Python script containing project logic
├─ 📁 pages
│  ├─ 📄 Academic.py (213 lines) - Python script containing project logic
│  ├─ 📄 Home.py (78 lines) - Python script containing project logic
│  ├─ 📄 Manage.py (553 lines) - Python script containing project logic
│  ├─ 📄 Search.py (672 lines) - Python script containing project logic
│  └─ 📄 __init__.py (4 lines) - Python script containing project logic
├─ 📁 src
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 academic_metadata.py (37 lines) - Python script containing project logic
│  ├─ 📄 academic_response_processor.py (202 lines) - Python script containing project logic
│  ├─ 📄 base_metadata.py (101 lines) - Python script containing project logic
│  ├─ 📄 citation_metadata.py (199 lines) - Python script containing project logic
│  ├─ 📄 config_manager.py (110 lines) - Python script containing project logic
│  ├─ 📄 document_validator.py (118 lines) - Python script containing project logic
│  ├─ 📄 equation_extractor.py (15 lines) - Python script containing project logic
│  ├─ 📄 equation_metadata.py (148 lines) - Python script containing project logic
│  ├─ 📄 file_manager.py (113 lines) - Python script containing project logic
│  ├─ 📄 file_processor.py (479 lines) - Python script containing project logic
│  ├─ 📄 lightrag_helpers.py (185 lines) - Python script containing project logic
│  ├─ 📄 lightrag_init.py (236 lines) - Python script containing project logic
│  ├─ 📄 metadata_consolidator.py (224 lines) - Python script containing project logic
│  ├─ 📄 metadata_extractor.py (661 lines) - Python script containing project logic
│  └─ 📄 pdf_converter.py (301 lines) - Python script containing project logic
└─ 📁 tests
   ├─ 📄 test_citation_processor.py (166 lines) - Python script containing project logic
   ├─ 📄 test_metadata.py (331 lines) - Python script containing project logic
   └─ 📁 cli
      ├─ 📄 test_pdf_cmd.py (113 lines) - Python script containing project logic
      ├─ 📄 test_search_cmd.py (145 lines) - Python script containing project logic
      └─ 📄 test_store_cmd.py (119 lines) - Python script containing project logic

# 🔍 Key Files with Methods

`pages/Academic.py` (213 lines)
Functions:
- any
- create_citation_network
- load_metadata_files
- main
- nodes
- show_academic

`src/academic_metadata.py` (37 lines)
Functions:
- AcademicMetadata
- Citation

`src/academic_response_processor.py` (202 lines)
Functions:
- AcademicResponseProcessor
- _add_citations
- _format_equations
- _format_references
- format_academic_response
- process_response
- replace_citation
- save_academic_response

`src/base_metadata.py` (101 lines)
Functions:
- AcademicMetadata
- Author
- Reference
- ensure_names
- model_dump
- parse_name
- to_dict

`src/citation_metadata.py` (199 lines)
Functions:
- CitationLink
- CitationLocation
- CitationProcessor
- _find_matching_reference
- _get_context
- _get_location
- get_citation_graph
- len
- process_citations
- to_citation
- validate_citations

`cli/core/config.py` (89 lines)
Functions:
- ConfigManager
- PDFEngine
- ProcessingConfig
- _load_config
- _save_config
- get_processing_config
- get_store_root
- validate_store_path

`src/config_manager.py` (110 lines)
Functions:
- ConfigManager
- PDFEngine
- ProcessingConfig
- get_config
- is_file
- validate_file

`src/document_validator.py` (118 lines)
Functions:
- DocumentValidator
- strip
- validate_content
- validate_file
- validate_files
- validate_store

`src/equation_extractor.py` (15 lines)
Functions:
- Equation

`src/equation_metadata.py` (148 lines)
Functions:
- Equation
- EquationExtractor
- EquationType
- _debug_print
- _extract_symbols
- extract_equations
- model_dump
- search

`cli/core/errors.py` (40 lines)
Functions:
- LightRAGError
- MetadataError
- PDFProcessingError
- SearchError
- StoreError
- handle_error

`src/file_manager.py` (113 lines)
Functions:
- create_store_directory
- ensure_db_exists

`src/file_processor.py` (479 lines)
Functions:
- FileProcessor
- _convert_pdf_with_marker
- _ensure_marker_initialized
- _extract_metadata_with_doi
- _extract_text
- _get_metadata_path
- _get_text_path
- _load_metadata
- _try_doi_extraction
- _validate_file
- clean_unused_files
- glob
- is_supported_file
- lower
- process_file
- set_store_path

`pages/Home.py` (78 lines)
Functions:
- show_home

`src/lightrag_helpers.py` (185 lines)
Functions:
- ResponseProcessor
- create_response_metadata
- extract_key_points
- format_full_response
- format_sources
- process_response
- save_response_history

`src/lightrag_init.py` (236 lines)
Functions:
- EmbeddingFunc
- LightRAGManager
- _configure_rag
- _get_store_size
- based
- get_stats
- load_documents
- query

`cli/main.py` (37 lines)
Functions:
- cli
- version

`pages/Manage.py` (553 lines)
Functions:
- button
- init_session_state
- len
- process_files
- show_manage
- update_status

`src/metadata_consolidator.py` (224 lines)
Functions:
- MetadataConsolidator
- _load_json
- _save_json
- initialize_consolidated_json
- remove_document_metadata
- update_document_metadata

`src/metadata_extractor.py` (661 lines)
Functions:
- MetadataExtractor
- _extract_abstract
- _extract_authors
- _extract_references_section
- _extract_references_with_anystyle
- _extract_title
- _parse_authors
- _parse_from_text
- _parse_references
- extract_metadata
- hasattr
- isinstance

`cli/commands/pdf_cmd.py` (159 lines)
Functions:
- info
- list
- pdf
- process
- update_progress

`src/pdf_converter.py` (301 lines)
Functions:
- MarkerConverter
- PDFConverter
- PDFConverterFactory
- PyMuPDFConverter
- PyPDF2Converter
- _extract_text_from_blocks
- _get_crossref_metadata
- create_converter
- extract_metadata
- extract_text
- hasattr

`cli/core/progress.py` (33 lines)
Functions:
- ProgressCallback
- ProgressManager
- get_callback
- update

`pages/Search.py` (672 lines)
Functions:
- button
- check_lightrag_ready
- clear_chat_history
- expander
- export_chat_history
- form
- get_conversation_context
- manage_conversation_context
- replace
- rewrite_prompt
- should_summarize_conversation
- show_search
- spinner
- status
- summarize_conversation
- update_conversation_with_summary

`cli/commands/search_cmd.py` (194 lines)
Functions:
- graph
- query
- search
- stats

`cli/commands/store_cmd.py` (115 lines)
Functions:
- create
- delete
- info
- list
- store

`cli/core/store_manager.py` (229 lines)
Functions:
- StoreManager
- create_store
- delete_store
- get_store
- get_store_info
- is_dir
- iterdir
- list_stores
- store_exists
- update_store_metadata
- validate_store_path

`tests/test_citation_processor.py` (166 lines)
Functions:
- sample_references
- test_author_year_citation_processing
- test_citation_context_extraction
- test_citation_graph_generation
- test_citation_validation
- test_cross_reference_citation_processing
- test_mixed_citation_styles
- test_numeric_citation_processing

`tests/test_metadata.py` (331 lines)
Functions:
- config_manager
- file_processor
- processed_files
- test_arxiv_metadata_extraction
- test_citation_extraction
- test_complete_pipeline
- test_consolidated_metadata
- test_doi_metadata_extraction
- test_equation_extraction

`tests/cli/test_pdf_cmd.py` (113 lines)
Functions:
- runner
- test_env
- test_list_empty_store
- test_list_pdfs
- test_pdf_info
- test_pdf_info_nonexistent
- test_process_nonexistent_pdf
- test_process_nonexistent_store
- test_process_pdf

`tests/cli/test_search_cmd.py` (145 lines)
Functions:
- patch
- runner
- test_env
- test_graph_command
- test_graph_nonexistent_store
- test_query_command
- test_query_nonexistent_store
- test_query_with_graph
- test_stats_command
- test_stats_nonexistent_store

`tests/cli/test_store_cmd.py` (119 lines)
Functions:
- runner
- test_create_existing_store
- test_create_store
- test_delete_nonexistent_store
- test_delete_store
- test_env
- test_list_empty_stores
- test_list_stores
- test_store_info

# 📊 Project Overview
**Files:** 38  |  **Lines:** 6,501

## 📁 File Distribution
- .py: 38 files (6,501 lines)

*Updated: January 19, 2025 at 11:08 AM*