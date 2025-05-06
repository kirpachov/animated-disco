FROM python:3.9-slim

WORKDIR /app

# Installazione dipendenze di sistema ottimizzate
RUN apt-get update && \
    apt-get install -y --no-install-recommends libimage-exiftool-perl && \
    rm -rf /var/lib/apt/lists/*

COPY ./app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

# Crea la cartella uploads con permessi ottimizzati
RUN mkdir -p /app/uploads && \
    chmod 777 /app/uploads

# Ottimizzazione per le prestazioni
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UVICORN_WORKERS=4 \
    UVICORN_LIMIT_MAX_REQUESTS=10000 \
    UVICORN_LIMIT_CONCURRENCY=1000

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "4"]