# AWS Deployment Guide

## Overview

This guide explains how to deploy the GNOME Code Assistant to AWS using ECS Fargate or Elastic Beanstalk.

## Prerequisites

1. **AWS CLI** installed and configured
2. **Docker** installed locally
3. **AWS Account** with appropriate permissions

## Option 1: AWS ECS Fargate (Recommended)

### 1. Build and Push Docker Image

```bash
# Set your AWS account ID and region
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export SERVICE_NAME="gnome-assistant"

# Build the image
docker build -f deployments/aws/Dockerfile -t $SERVICE_NAME .

# Tag for ECR
docker tag $SERVICE_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$SERVICE_NAME:latest

# Push to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$SERVICE_NAME:latest
```

### 2. Create ECS Cluster

```bash
# Create cluster
aws ecs create-cluster --cluster-name gnome-assistant-cluster

# Create task definition
cat > task-definition.json << EOF
{
  "family": "gnome-assistant",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "gnome-assistant",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$SERVICE_NAME:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OPENAI_API_KEY",
          "value": "your_key_here"
        },
        {
          "name": "DEBUG",
          "value": "false"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/gnome-assistant",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### 3. Create ECS Service

```bash
# Create service
aws ecs create-service \
    --cluster gnome-assistant-cluster \
    --service-name gnome-assistant-service \
    --task-definition gnome-assistant:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

## Option 2: AWS Elastic Beanstalk

### 1. Create Application

```bash
# Create application
eb init gnome-assistant --platform "Docker running on 64bit Amazon Linux 2"

# Create environment
eb create gnome-assistant-prod --instance-type t3.medium
```

### 2. Configure Environment Variables

```bash
# Set environment variables
eb setenv OPENAI_API_KEY="your_key_here" DEBUG=false
```

### 3. Deploy

```bash
# Deploy application
eb deploy
```

## Option 3: AWS Lambda (Serverless)

For serverless deployment, you'd need to create a separate `lambda_handler.py` that wraps the agent logic.

## Environment Variables

Set these in your deployment:

- `OPENAI_API_KEY`: Your OpenAI API key
- `DEBUG`: Set to `false` for production
- `PORT`: Application port (8000 for ECS, auto for Beanstalk)

## Monitoring and Logging

### CloudWatch Logs
```bash
# View logs
aws logs describe-log-groups --log-group-name-prefix "/ecs/gnome-assistant"
aws logs tail /ecs/gnome-assistant --follow
```

### CloudWatch Metrics
- Monitor CPU and memory usage
- Set up alarms for errors
- Track request latency

## Security

1. **IAM Roles**: Use least privilege principle
2. **VPC**: Deploy in private subnets
3. **Secrets Manager**: Store API keys securely
4. **WAF**: Protect against common attacks

## Cost Optimization

1. **Right-size Instances**: Monitor and adjust
2. **Auto Scaling**: Scale based on demand
3. **Reserved Instances**: For predictable workloads
4. **Spot Instances**: For non-critical workloads

## Troubleshooting

### Common Issues

1. **Memory Issues**: Increase memory allocation
2. **Timeout**: Increase timeout for long operations
3. **Network**: Check security groups and subnets
4. **Logs**: Check CloudWatch logs

### Debug Commands

```bash
# Check service status
aws ecs describe-services --cluster gnome-assistant-cluster --services gnome-assistant-service

# View recent logs
aws logs tail /ecs/gnome-assistant --since 1h

# Test locally
docker run -p 8000:8000 -e OPENAI_API_KEY="your_key" $SERVICE_NAME
```

## Scaling Configuration

```bash
# Update service desired count
aws ecs update-service \
    --cluster gnome-assistant-cluster \
    --service gnome-assistant-service \
    --desired-count 3
```

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and Deploy
        run: |
          docker build -f deployments/aws/Dockerfile -t gnome-assistant .
          docker tag gnome-assistant:latest ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/gnome-assistant:latest
          docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/gnome-assistant:latest
          aws ecs update-service --cluster gnome-assistant-cluster --service gnome-assistant-service --force-new-deployment
```



