#!/bin/bash

# Ensure AWS credentials are current
echo "Ensuring AWS credentials are current..."
saml2aws login

# Set AWS profile
export AWS_PROFILE=saml

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
sam build --profile saml

# Deploy the application
# You can modify the stack name as needed
sam deploy --guided --profile saml --stack-name ai-interview-app

echo "Deployment completed!" 