FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install gst-engine (editable so rules/ path resolution works)
COPY gst-engine /gst-engine
RUN pip install --no-cache-dir -e /gst-engine

# Install backend deps (strip the local -e ../gst-engine line — already installed above)
COPY backend/requirements.txt .
RUN grep -v 'gst-engine' requirements.txt | pip install --no-cache-dir -r /dev/stdin

COPY backend/ .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
