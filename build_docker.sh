#!/bin/bash
# Build Docker image
docker build -t aif-converter .

# Run the container
# docker run -d -p 5000:5000 --name aif-web aif-converter
