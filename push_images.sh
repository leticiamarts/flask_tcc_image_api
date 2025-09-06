#!/bin/bash
set -e

DOCKER_USERNAME="leticiamartins11"

echo "Building Flask API image..."
docker build -t $DOCKER_USERNAME/flask-api:latest ./api

echo "Pushing Flask API image..."
docker push $DOCKER_USERNAME/flask-api:latest

echo "Building Streamlit UI image..."
docker build -t $DOCKER_USERNAME/streamlit-ui:latest ./frontend

echo "Pushing Streamlit UI image..."
docker push $DOCKER_USERNAME/streamlit-ui:latest

echo "Done!"