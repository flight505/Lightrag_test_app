# LightRAG: Advanced Academic Research Assistant 🎓

A sophisticated academic research tool combining knowledge graph capabilities with retrieval-augmented generation (RAG), optimized for academic paper analysis and research assistance.

## Architecture Overview 🏗️

<p align="center">
  <img src="https://private-user-images.githubusercontent.com/20601200/400261737-d59098dc-c84c-4c3d-b902-fb2215fa9f91.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MzYxMjMyNzMsIm5iZiI6MTczNjEyMjk3MywicGF0aCI6Ii8yMDYwMTIwMC80MDAyNjE3MzctZDU5MDk4ZGMtYzg0Yy00YzNkLWI5MDItZmIyMjE1ZmE5ZjkxLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAxMDYlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMTA2VDAwMjI1M1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTlmYzQxOTI3Nzk4N2NjYzI1YTk5MzVjZDY5ZDUzNzQzMGMyMTc1ZmFhMjQzMjIzZWEyYjRkYTQzZWFlNmQ3N2MmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.3AMezH-z6Nbms9EjtTya_XtgFiVbmwYcIPnCuLbpO9c" alt="LightRAG Architecture" width="100%">
</p>

Our system enhances the core LightRAG framework with specialized academic components:

### Academic Enhancement Layer
- **Academic Metadata Processor**: Handles author tracking, citation management, DOI extraction, and equation processing with robust validation
- **Enhanced File Processor**: Optimized for academic PDFs with LaTeX equation extraction and pattern recognition
- **Academic Response Processor**: Generates responses in academic style with proper citations and source attribution

### Core LightRAG Integration
The academic components seamlessly integrate with LightRAG's:
- Document ingestion pipeline for processing academic papers
- Multi-modal storage layer (Vector DB, Knowledge Graph, KV Store)
- Sophisticated retrieval pipeline with multiple query modes

## Key Features 🌟

- **Advanced PDF Processing**: Optimized PDF conversion on Apple Silicon and Marker
- **Academic Metadata Extraction**: Comprehensive tracking of authors, references, equations and citations
- **Multi-Mode Search**: Naive, Local, Global, Hybrid, and Mix search strategies
- **LaTeX Support**: Advanced equation extraction and processing with context preservation
- **Citation Management**: Multiple citation styles (APA, MLA, Chicago, IEEE)
- **Academic Response Generation**: Structured responses with source tracking

## Installation 🔧

1. Clone the repository:
```bash
git clone https://github.com/yourusername/lightrag.git
cd lightrag
```

2. Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
pip install uv
uv pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export OPENAI_API_KEY="your-api-key"
```

## Usage 🚀

1. Initialize the workspace:
```bash
python src/lightrag_init.py --init
```

2. Run the Streamlit interface:
```bash
streamlit run main.py
```

## Search Modes 🔍

- **Naive**: Basic document search
- **Local**: Context-aware document analysis
- **Global**: Broad knowledge base search
- **Hybrid**: Combined local and global search
- **Mix**: Adaptive search strategy

## Academic Features 📚

### Metadata Processing
- Multiple validation levels (Basic, Standard, Strict)
- Equation type classification
- Author affiliation tracking
- DOI and venue extraction
- Citation network analysis

### Document Processing
- LaTeX equation extraction
- Reference pattern matching
- Batch processing with progress tracking
- Source preservation and validation

## Configuration ⚙️

Default settings optimized for academic papers:
- Chunk size: 500
- Chunk overlap: 50
- Temperature: Configurable per use case
- Sentence-based chunking

## Models 🤖

Supported models:
- gpt-4o (recommended for complex analysis)
- gpt-4o-mini (default)
- o1-mini
- o1

## Error Handling and Logging 📝

- Comprehensive try-except blocks
- Color-coded terminal output
- Progress tracking
- Detailed error context

## Best Practices 💡

- UTF-8 encoding throughout
- Environment variable configuration
- Parallel processing where applicable
- Separation of concerns
- Comprehensive error handling

## Contributing 🤝

We welcome contributions! Please read our contributing guidelines and submit pull requests. Our academic enhancements focus on:

1. Improving academic metadata extraction
2. Enhancing LaTeX and equation handling
3. Expanding citation style support
4. Optimizing academic response generation

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏

- Built upon GraphRAG concepts
- Optimized for academic research
- Enhanced with advanced metadata processing
- Special thanks to the academic research community

---

For detailed documentation, visit our [Wiki](https://github.com/yourusername/lightrag/wiki).

Happy Researching! 📚✨