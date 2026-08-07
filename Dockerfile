FROM python:3.11-slim

WORKDIR /app

# Completely different RUN command to kill the cache
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    ffmpeg \
    git \
    build-essential \
    zstd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN curl -fsSL https://ollama.com/install.sh | sh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]