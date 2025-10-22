FROM python:3.11-slim

WORKDIR /app

# System deps (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy project
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Env: allow configurable codebase root (defaults handled in config.py)
ENV PORT=8000

EXPOSE 8000

CMD ["python", "app.py"]
