# Deployment Guide

This project is designed to be **cloud-agnostic** and can be deployed to any cloud provider or on-premises infrastructure.

## 🏗️ Architecture

The main application (`app.py`) is a **cloud-agnostic FastAPI application** that:
- Uses environment variables for configuration
- Supports any port via `PORT` environment variable
- Includes health checks and monitoring endpoints
- Works with any container orchestration platform

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your_key_here"
export DEBUG=true

# Run the application
python app.py
```

### Docker
```bash
# Build image
docker build -t gnome-assistant .

# Run container
docker run -p 8000:8000 -e OPENAI_API_KEY="your_key_here" gnome-assistant
```

## ☁️ Cloud Deployment Options

### 1. Azure
- **Service**: Azure App Service, Container Instances, or AKS
- **Guide**: [deployments/azure/azure-deploy.md](deployments/azure/azure-deploy.md)
- **Features**: Azure-specific health checks, background tasks

### 2. Google Cloud Platform
- **Service**: Cloud Run, GKE, or App Engine
- **Guide**: [deployments/gcp/deploy.md](deployments/gcp/deploy.md)
- **Features**: Optimized for Cloud Run, auto-scaling

### 3. AWS
- **Service**: ECS Fargate, Elastic Beanstalk, or EKS
- **Guide**: [deployments/aws/deploy.md](deployments/aws/deploy.md)
- **Features**: ECS task definitions, CloudWatch integration

### 4. Other Platforms
The main `app.py` works on any platform that supports:
- Python 3.11+
- FastAPI/uvicorn
- Environment variables
- Port binding

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
DEBUG=true                    # Enable debug mode
PORT=8000                     # Application port
SOURCE_DIRECTORY=/app/gdm     # Source code directory
VECTORSTORE_PATH=/app/vectorstore/faiss_index  # Vector store path
```

### Configuration File
All settings are centralized in `config.py` and can be overridden with environment variables.

## 📊 Monitoring

### Health Endpoints
- `GET /health`: Application health check
- `GET /config`: Current configuration
- `GET /rebuild/status`: Vectorstore rebuild status

### Metrics
- Response times
- Memory usage
- Token consumption
- Error rates

## 🔒 Security

### Production Checklist
- [ ] Set `DEBUG=false`
- [ ] Use environment variables for secrets
- [ ] Configure CORS appropriately
- [ ] Enable HTTPS
- [ ] Set up proper IAM roles
- [ ] Use secrets management service
- [ ] Configure network security groups

## 🚀 Scaling

### Horizontal Scaling
- The application is stateless
- Use load balancers for multiple instances
- Configure auto-scaling based on CPU/memory

### Vertical Scaling
- Adjust memory allocation based on usage
- Monitor token consumption
- Optimize chunk sizes for your use case

## 🧪 Testing

### Local Testing
```bash
# Test the agent
python agent.py "explain the login process"

# Test the API
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "explain the login process"}'
```

### Production Testing
- Use the `/health` endpoint for load balancer health checks
- Monitor logs for errors
- Test with realistic workloads

## 🔄 CI/CD

### GitHub Actions Example
```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Cloud
        run: |
          # Your deployment commands here
```

## 📝 Best Practices

1. **Use environment variables** for all configuration
2. **Monitor resource usage** and scale accordingly
3. **Set up proper logging** and monitoring
4. **Use secrets management** for API keys
5. **Configure health checks** for your platform
6. **Test thoroughly** before production deployment
7. **Use container registries** for image storage
8. **Set up backup strategies** for vectorstore data

## 🆘 Troubleshooting

### Common Issues
1. **Memory issues**: Increase memory allocation
2. **Timeout errors**: Increase timeout settings
3. **CORS errors**: Configure CORS for your domain
4. **API key issues**: Check environment variables

### Debug Commands
```bash
# Check application logs
docker logs container_name

# Test health endpoint
curl http://localhost:8000/health

# Check configuration
curl http://localhost:8000/config
```

## 📞 Support

For deployment issues:
1. Check the platform-specific deployment guides
2. Review the application logs
3. Test locally first
4. Check environment variable configuration



