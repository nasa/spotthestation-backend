#!/bin/bash
set -euo pipefail

# Login into ECR and build the docker image
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
docker buildx build --platform=linux/amd64 --tag $IMG_TAG --load --file ./Dockerfile .
docker push $IMG_TAG

# Restart ECS services
aws ecs update-service --region $AWS_REGION --cluster $CLUSTER_NAME --service $SERVICE_NAME --no-cli-pager --force-new-deployment
