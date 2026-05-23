FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python -c \"import time, urllib.request; url='http://chromadb:8000/api/v1/heartbeat';\nfor attempt in range(1, 31):\n    try:\n        urllib.request.urlopen(url, timeout=3).read(); print('ChromaDB is ready'); break\n    except Exception as exc:\n        print(f'Waiting for ChromaDB ({attempt}/30): {exc}'); time.sleep(2)\nelse:\n    raise SystemExit('ChromaDB did not become ready after 30 attempts')\" && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
