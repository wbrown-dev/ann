FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANN_DIGEST_DIR=/data

WORKDIR /app

# Runtime deps only: requirements-dev.txt (pytest, ruff) never enters the image.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ann_app ./ann_app
COPY ann.py streamlit_app.py ./

# Digests are runtime state on a mounted volume, not baked image layers, so the
# app tree stays immutable and can run with a read-only root filesystem.
RUN useradd --create-home --uid 10001 ann \
    && mkdir -p /data \
    && chown -R ann:ann /data
VOLUME ["/data"]

USER ann

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').read()==b'ok' else 1)"

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
