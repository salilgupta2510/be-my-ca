FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "git+https://github.com/salilgupta2510/be-my-ca.git@main#subdirectory=gst-engine"

COPY requirements.txt .
RUN grep -v 'gst-engine' requirements.txt | pip install --no-cache-dir -r /dev/stdin

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
