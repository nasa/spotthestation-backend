#!/bin/bash
set -euo pipefail

# Fetch AWS secret values for CI
export AWS_REGION=us-east-1
export VER_TAG=latest
export ECR_REGISTRY=372510285487.dkr.ecr.us-east-1.amazonaws.com
export IMG_TAG=$ECR_REGISTRY/nasa-sts-backend:$VER_TAG
export CLUSTER_NAME=production
export SERVICE_NAME=nasa-sts-backend

echo "Building PRODUCTION BACKEND with image tag [$IMG_TAG]..."
./scripts/_deploy.sh
