FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
# pytest is only needed for tests, which run in CI rather than inside the image
RUN grep -v '^pytest' requirements.txt > requirements.runtime.txt && pip install -r requirements.runtime.txt

COPY . .
RUN chmod +x docker-entrypoint.sh && useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/health/live', timeout=3).status == 200 else 1)"
ENTRYPOINT ["./docker-entrypoint.sh"]
