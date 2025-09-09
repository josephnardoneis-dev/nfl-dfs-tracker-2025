#!/bin/bash
# Build script for Render deployment

echo "Python version:"
python --version

echo "Installing Python packages with pip..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Build completed successfully!"