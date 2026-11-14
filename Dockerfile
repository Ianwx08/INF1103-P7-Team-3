FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    TZ=Asia/Singapore

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY models/ ./models/
COPY managers/ ./managers/
COPY tests/ ./tests/
COPY samples/ ./samples/

VOLUME ["/app/data"]

CMD ["python", "main.py"]
