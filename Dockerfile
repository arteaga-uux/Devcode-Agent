FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 \
    GIT_DISCOVERY_ACROSS_FILESYSTEM=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential curl \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY . .
COPY .git .git

# DEBUG: verbose to surface the failing package
RUN pip install -v --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python","-m","uvicorn","my_agent.app:app","--host","0.0.0.0","--port","8000"]
