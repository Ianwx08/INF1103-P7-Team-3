# Use a lightweight Python 3.12 image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Configure Python, Singapore timezone and data storage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Singapore \
    DATA_DIR=/app/data

# Install Singapore timezone information
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

# Copy dependencies first to improve build caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application's Python files
COPY *.py ./

# Copy the OOP packages and automated tests
COPY models/ ./models/
COPY managers/ ./managers/
COPY tests/ ./tests/

# Create the data directory
RUN mkdir -p /app/data

# Declare the persistent data directory
VOLUME ["/app/data"]

# Start the application
CMD ["python", "main.py"]
