#!/bin/bash

# Declare PYTHONPATH if not set
: "${PYTHONPATH:=""}"

# Append current directory to PYTHONPATH
PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"
export PYTHONPATH

# Run streamlit app
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 