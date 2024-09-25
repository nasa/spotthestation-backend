#!/bin/bash
set -euo pipefail

# Fetch AWS secret values for CI
export AWS_REGION=us-east-2
export VER_TAG=latest
export ECR_REGISTRY=629235421780.dkr.ecr.us-east-2.amazonaws.com
export IMG_TAG=$ECR_REGISTRY/nasa-sts-backend:$VER_TAG
export CLUSTER_NAME=solwey-qa
export SERVICE_NAME=nasa-sts-backend

echo "Building QA BACKEND with image tag [$IMG_TAG]..."
./scripts/_deploy.sh
