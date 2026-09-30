FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models

WORKDIR /app

ARG TORCH_VERSION=2.14.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url "$TORCH_INDEX_URL" "torch==${TORCH_VERSION}" && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py extractor.py config.yaml ./

RUN useradd --uid 10001 --create-home gliner && \
    mkdir -p /models && chown gliner /models
USER gliner

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10m --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
