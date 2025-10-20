FROM python:3.13-slim

# Build argument for data directory
ARG DATA_DIR=/app/data

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DATA_DIR=${DATA_DIR}

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p ${DATA_DIR}

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Create volume for data persistence
VOLUME ["${DATA_DIR}"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
