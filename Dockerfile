FROM python:3.11-slim

# git needed by src/tools/repo.py for cloning analyzed repos
# ca-certificates for HTTPS to api.anthropic.com + api.github.com
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy install metadata first for Docker layer caching
COPY pyproject.toml ./

# Copy source
COPY src/ ./src/
COPY backend/ ./backend/

RUN pip install --no-cache-dir .

# Container Apps sets $PORT at runtime; default to 8000 for local
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT}"]