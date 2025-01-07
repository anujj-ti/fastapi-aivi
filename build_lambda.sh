#!/bin/bash

# Create a temporary directory for the build
mkdir -p build
rm -rf build/*

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy dependencies to build directory
cp -r venv/lib/python*/site-packages/* build/

# Copy application files
cp main.py build/
cp lambda_handler.py build/
cp llm.py build/
cp .env build/

# Create deployment package
cd build
zip -r ../deployment-package.zip .

# Clean up
cd ..
rm -rf build
rm -rf venv

echo "Deployment package created: deployment-package.zip" 