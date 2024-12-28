## Project Overview
The LightRAG application is designed to serve as a comprehensive tool for academic research and writing academic papers, providing a user-friendly interface for querying and visualizing graph-based data. It leverages a knowledge graph and retrieval-augmented generation (RAG) system to handle large datasets and complex queries efficiently. It has a Agentic mode that can use the KG RAG system to write long form reports. Key features include:

- **Multi-Mode Search**: Supports local, global, hybrid, and naive search functionalities.
- **File Handling**: Converts various document formats (docx, text, pdf) to .txt and organizes them into a "converted" subfolder.
- **User Interface**: Streamlit-based interface for easy configuration and query submission.
- **Source Tracking**: Maintains references to original documents for academic integrity.
- **Equation Handling**: Extracts and renders LaTeX equations for better understanding.

- **Search Functionality**:
**Implementation**: Located in `pages/1_Search.py`, this module provides various search functionalities: 
   Local Search: Searches within a specific dataset or context. 
   Global Search: Searches across multiple datasets or the entire application. 
   Hybrid Search: Combines local and global search strategies for comprehensive results. 
   Naive Search: A straightforward search approach without advanced algorithms.

- **Preprocessing**: Uses `src/file_processor.py` to convert files to .txt format, including PDF conversion with Marker.
- **Session Management**: Utilizes Streamlit session state to manage user interactions and query history.
- **Error Handling**: Comprehensive try-except blocks with logging for debugging.
- **Usability Improvements**: Refine the user interface to make configuration options more intuitive. Add tooltips and help sections for new users.
- **Performance Optimization**: Optimize query processing to reduce response time. Implement caching mechanisms for frequently accessed data.
- **Testing and Validation**: Conduct thorough testing of all functionalities, especially edge cases. Suggestion: Use automated testing frameworks to ensure reliability.

## Main files:

1. `src/file_manager.py`: Contains functions for creating document directories and updating the `.gitignore` file to manage file storage and exclusion.

2. `pages/1_Search.py`: Implements the Streamlit interface for search and chat modes, managing session states and processing queries with progress updates. Includes store selection, file scanning, and PDF conversion.

3. `src/lightrag_helpers.py`: Includes helper functions for processing LightRAG responses, managing sources, formatting responses, and handling LaTeX equations.

4. `src/global_helper_functions.py`: Contains functions for mapping generated responses to source documents and creating traceability tables for global search.

5. `src/Graph_query.py`: Sets up the Streamlit page configuration for querying the knowledge base using LightRAG.

6. `src/lightrag_init.py`: Manages the initialization and configuration of LightRAG, including document loading, validation, and query execution. Integrates with DocumentValidator for file and content validation.

7. `src/local_helper_functions.py`: Provides functions for local search post-processing, mapping responses to source documents, and creating traceability tables.

8. `src/document_validator.py`: Implements comprehensive document validation including:
   - File validation (existence, format, encoding)
   - Content validation (emptiness, minimum length)
   - Store validation (structure, file collection)
   - Error reporting and logging

9. `src/file_processor.py`: Handles file preprocessing, including PDF conversion to text using Marker, and tracks file metadata.

The document validation system ensures data quality by:
- Validating files before processing
- Checking content integrity
- Providing detailed error feedback
- Maintaining validation logs
- Supporting the LightRAG initialization process

## Helper Functions

1. **Global Helpers**:
   - **Purpose**: Manage the mapping of generated responses to source documents, ensuring traceability and context for global search.
   - **Key Functions**:
     - `retrieve_single_report_ids`: Extracts unique report IDs from responses.
     - `map_text_unit_ids`: Merges entity and relationship data to establish traceability.
     - `map_text_unit_content`: Associates text content with traceability data.
     - `map_titles`: Maps document titles to traceability data.
     - `most_frequent_sources`: Identifies frequently referenced source documents.
     - `create_traceability`: Primary function to map responses to source documents.
     - `combine_query_response_sources`: Formats query, response, and most frequent sources.
     - `combine_query_supporting_analysis`: Formats query and key supporting analyses.

2. **Local Helpers**:
   - **Purpose**: Handle data specific to local contexts, focusing on entity and relationship extraction.
   - **Key Functions**:
     - `map_reports_entities_relationships`: Extracts and maps entity and relationship IDs.
     - `map_text_unit_ids`: Maps text unit IDs and source IDs to the traceability table.
     - `map_text_unit_content`: Maps text content to the traceability table.
     - `map_titles`: Maps document titles to the traceability table.
     - `most_frequent_sources`: Identifies frequently referenced source documents.
     - `create_traceability`: Primary function to map responses to source documents.
     - `combine_query_response_sources`: Formats query, response, and most frequent sources.
     - `retrieve_text_units`: Retrieves text units corresponding to the response.

## Coding Standards
- **Language**: Python 3.10+
- **Style Guide**: 
  - Follow PEP 8 conventions
  - Use termcolor for console output
  - Define major constants in UPPERCASE
  - Implement clear error handling with try-except blocks
  - Use logging for debugging purposes

## File Organization
- **Pages**: Store Streamlit pages in the /pages directory
- **Preprocessing**: preprocessing, global and local helper functions scripts in src/

## Best Practices
1. **Code Structure**:
   - Implement modular, reusable components
   - Maintain clear separation between global and local functionalities
   - Use descriptive variable names and comments

2. **Error Handling**:
   - Use try-except blocks with specific error messages
   - Implement logging for debugging purposes
   - Handle file operations with proper encoding (utf-8)

3. **Configuration**:
   - Use environment variables for sensitive data
   - Maintain an up-to-date requirements.txt
   - Avoid hardcoding configuration values

## Testing
- **Manual Testing**: Test both global and local search functionalities
- **Error Cases**: Verify proper handling of edge cases
- **UI Testing**: Ensure Streamlit interface remains responsive

## Objectives

1. **Implement Source Tracking**:
   - Ensure that sources are correctly extracted and returned in the query response.
   - Explore alternative methods for source tracking that are compatible with `QueryParam`.

2. **Add Initialization Checks**:
   - Prevent errors when users submit queries before LightRAG is initialized.
   - Provide clear feedback to the user if LightRAG is not ready.

4. **Enhance Error Handling**:
   - Implement more specific error handling for different scenarios.
   - Provide user-friendly error messages with guidance on resolving issues.

6. **Optimize File Processing**:
   - GPU selection for pdf processing, MPS, CUDA or CPU. 
   - Ensure that PDF conversion is done correctly and only when needed.

7. **Improve User Experience**:
   - Refine the user interface to make configuration options more intuitive.
   - Add tooltips and help sections for new users.
   - Add a progress bar for the pdf processing. 
   - Make sure we use Google Material Symbols (rounded style), using the syntax :material/icon_name:, where "icon_name" is the name of the icon in snake case. For a complete list of icons, see Google's Material Symbols font library.

8. **Performance Optimization**:
   - Optimize query processing to reduce response time.
   - Implement caching mechanisms for frequently accessed data.

9. **Agentic Mode**:
   - Implement an agentic mode that can use the KG RAG system to write long form reports. 
   - corectly add sources and references to the report. 

10. **Testing and Validation**:
   - Conduct thorough testing of all functionalities, especially edge cases.
   - Use automated testing frameworks to ensure reliability.
