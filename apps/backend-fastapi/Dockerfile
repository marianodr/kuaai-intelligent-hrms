FROM python:3.12-slim AS base
WORKDIR /app

# Dependencias del sistema para docling y psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc g++ libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY . .
# Pre-descarga el modelo de embeddings para no depender de red en runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
