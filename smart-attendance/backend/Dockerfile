FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    curl \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data /data/photos

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--h11-max-incomplete-event-size", "65536"]
