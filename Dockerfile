FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential curl \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

# Short-circuit SCM-based versioning to avoid git lookups
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0

# Copy code first (lets some build backends inspect project metadata)
COPY . .

# If SCM errors persist, uncomment next line and ensure .dockerignore doesn't exclude .git
# COPY .git .git

RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

EXPOSE 8000
CMD ["python","-m","uvicorn","my_agent.app:app","--host","0.0.0.0","--port","8000"]
