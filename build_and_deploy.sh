#!/bin/bash

# Ensure AWS credentials are current
echo "Ensuring AWS credentials are current..."
saml2aws login

# Set AWS profile
export AWS_PROFILE=saml

# Clean previous builds
rm -rf .aws-sam
rm -rf package

# Create a directory for the Lambda package
mkdir -p package

# Copy application files first
cp main.py package/
cp lambda_handler.py package/
cp llm.py package/
cp requirements.txt package/

# Change to package directory and install dependencies
cd package
pip install -r requirements.txt -t .
cd ..

# Build SAM application
sam build

# Deploy the application
sam deploy --guided --profile saml --stack-name ai-interview-app

echo "Deployment completed!" 