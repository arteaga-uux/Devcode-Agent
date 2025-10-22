# Azure Deployment Guide

## Overview

This guide explains how to deploy the GNOME Code Assistant to Azure using FastAPI instead of Flask.

## Why FastAPI over Flask?

1. **Better Performance**: FastAPI is built on Starlette and uses async/await
2. **Automatic API Documentation**: Built-in OpenAPI/Swagger docs at `/docs`
3. **Type Safety**: Pydantic models for request/response validation
4. **Azure Integration**: Better support for Azure App Service and Container Instances
5. **Production Ready**: Built-in features for production deployment

## Deployment Options

### Option 1: Azure App Service (Recommended)

1. **Create Azure App Service**:
   ```bash
   az webapp create --resource-group myResourceGroup --plan myAppServicePlan --name gnome-assistant --runtime "PYTHON|3.11"
   ```

2. **Configure Environment Variables**:
   ```bash
   az webapp config appsettings set --resource-group myResourceGroup --name gnome-assistant --settings OPENAI_API_KEY="your_key_here"
   ```

3. **Deploy via Git**:
   ```bash
   git add .
   git commit -m "Azure deployment"
   git push azure main
   ```

### Option 2: Azure Container Instances

1. **Build and Push Docker Image**:
   ```bash
   docker build -t gnome-assistant .
   docker tag gnome-assistant your-registry.azurecr.io/gnome-assistant:latest
   docker push your-registry.azurecr.io/gnome-assistant:latest
   ```

2. **Deploy Container**:
   ```bash
   az container create --resource-group myResourceGroup --name gnome-assistant --image your-registry.azurecr.io/gnome-assistant:latest --ports 8000 --environment-variables OPENAI_API_KEY="your_key_here"
   ```

### Option 3: Azure Functions (Serverless)

For serverless deployment, you'd need to create a separate `function_app.py` that wraps the agent logic.

## Key Changes for Azure

### 1. FastAPI Application (`azure_app.py`)
- Async endpoints for better performance
- Background tasks for vectorstore rebuilding
- Health checks for Azure load balancer
- CORS middleware for web frontend
- Pydantic models for type safety

### 2. Environment Configuration
- Uses `PORT` environment variable (Azure standard)
- Configurable via Azure App Settings
- Supports both OpenAI and Azure OpenAI

### 3. Health Endpoints
- `/health`: General health check
- `/azure/health`: Azure-specific health check
- `/azure/ready`: Readiness probe

### 4. Background Processing
- Vectorstore rebuilding happens in background
- Status tracking via `/rebuild/status`
- Non-blocking API responses

## API Endpoints

### Core Endpoints
- `POST /query`: Query the agent
- `POST /rebuild`: Trigger vectorstore rebuild
- `GET /rebuild/status`: Check rebuild status
- `GET /health`: Health check
- `GET /config`: Get current configuration

### Documentation
- `GET /docs`: Interactive API documentation (Swagger UI)
- `GET /redoc`: Alternative API documentation

## Testing Locally

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your_key_here"
   export DEBUG=true
   ```

3. **Run the application**:
   ```bash
   python azure_app.py
   ```

4. **Test endpoints**:
   ```bash
   curl -X POST "http://localhost:8000/query" \
        -H "Content-Type: application/json" \
        -d '{"query": "explain the login process"}'
   ```

## Production Considerations

### 1. Security
- Configure CORS origins properly
- Use Azure Key Vault for secrets
- Enable HTTPS only
- Set up authentication if needed

### 2. Performance
- Use Azure Redis Cache for session storage
- Configure auto-scaling
- Monitor with Azure Application Insights

### 3. Monitoring
- Set up Azure Application Insights
- Configure alerts for errors
- Monitor response times and throughput

### 4. File Storage
- Use Azure Blob Storage for vectorstore persistence
- Configure backup strategies
- Handle file uploads securely

## Cost Optimization

1. **Use Azure App Service Free Tier** for development
2. **Scale down during off-hours** using Azure Automation
3. **Use Azure Container Instances** for burst workloads
4. **Monitor usage** with Azure Cost Management

## Troubleshooting

### Common Issues
1. **Port binding**: Ensure `PORT` environment variable is set
2. **Memory limits**: Monitor memory usage in Azure portal
3. **Timeout issues**: Configure appropriate timeout values
4. **CORS errors**: Check CORS configuration in production

### Logs
- View logs in Azure App Service logs
- Use `az webapp log tail` for real-time logs
- Check Application Insights for detailed telemetry
