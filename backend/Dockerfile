FROM python:3.11-slim

# System dependencies for audio + PDF processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies first for better caching
COPY requirements.txt .
# Upgrade build tools first, then install requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# User environment variables from docker-compose or .env
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
