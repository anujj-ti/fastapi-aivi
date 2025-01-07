#!/bin/bash

# Clean previous builds
rm -rf .aws-sam

# Install dependencies in a requirements directory
mkdir -p .aws-sam/build/requirements
pip install -r requirements.txt -t .aws-sam/build/requirements

# Copy application files
cp main.py .aws-sam/build/requirements/
cp lambda_handler.py .aws-sam/build/requirements/
cp llm.py .aws-sam/build/requirements/

# Build SAM application
sam build

# Deploy the application
# You can modify the stack name as needed
sam deploy --guided --stack-name ai-interview-app

echo "Deployment completed!" 