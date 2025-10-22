# Google Cloud Platform Deployment Guide

## Overview

This guide explains how to deploy the GNOME Code Assistant to Google Cloud Platform using Cloud Run.

## Prerequisites

1. **Google Cloud SDK** installed and configured
2. **Docker** installed locally
3. **Google Cloud Project** with billing enabled

## Deployment Steps

### 1. Build and Push Docker Image

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export SERVICE_NAME="gnome-assistant"

# Build the image
docker build -f deployments/gcp/Dockerfile -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME
```

### 2. Deploy to Cloud Run

```bash
# Deploy the service
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars OPENAI_API_KEY="your_key_here" \
    --set-env-vars DEBUG=false \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10
```

### 3. Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service $SERVICE_NAME \
    --domain your-domain.com \
    --region us-central1
```

## Environment Variables

Set these in Cloud Run:

- `OPENAI_API_KEY`: Your OpenAI API key
- `DEBUG`: Set to `false` for production
- `PORT`: Cloud Run sets this automatically (8080)
- `SOURCE_DIRECTORY`: Path to your source code (default: `/app/gdm`)

## Monitoring and Logging

### View Logs
```bash
gcloud logs read --service=$SERVICE_NAME --limit=50
```

### Monitor Performance
- Use **Cloud Monitoring** for metrics
- Set up **Cloud Alerting** for errors
- Monitor **Cloud Run** metrics in the console

## Cost Optimization

1. **Set Memory Limits**: Adjust based on your usage
2. **Configure Scaling**: Set min/max instances
3. **Use Preemptible**: For non-critical workloads
4. **Monitor Usage**: Use Cloud Billing reports

## Security

1. **IAM Roles**: Use least privilege principle
2. **VPC**: Deploy in private network if needed
3. **Secrets**: Use Secret Manager for API keys
4. **HTTPS**: Cloud Run provides HTTPS by default

## Troubleshooting

### Common Issues

1. **Memory Issues**: Increase memory allocation
2. **Timeout**: Increase timeout for long operations
3. **Cold Starts**: Use min instances > 0
4. **CORS**: Configure CORS in your app

### Debug Commands

```bash
# Check service status
gcloud run services describe $SERVICE_NAME --region us-central1

# View recent logs
gcloud logs read --service=$SERVICE_NAME --limit=100

# Test locally
docker run -p 8080:8080 -e OPENAI_API_KEY="your_key" gcr.io/$PROJECT_ID/$SERVICE_NAME
```

## Scaling Configuration

```bash
# Update scaling settings
gcloud run services update $SERVICE_NAME \
    --region us-central1 \
    --min-instances 1 \
    --max-instances 20 \
    --concurrency 100
```

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Google Cloud SDK
        uses: google-github-actions/setup-gcloud@v0
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}
      
      - name: Build and Deploy
        run: |
          docker build -f deployments/gcp/Dockerfile -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/gnome-assistant .
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/gnome-assistant
          gcloud run deploy gnome-assistant --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/gnome-assistant --region us-central1 --platform managed
```



