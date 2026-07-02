# Speedrun AI proxy: a tiny OpenAI-compatible reverse proxy that holds the real
# OpenAI key server-side, so it never ships in the desktop/phone client.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

ENV PORT=8080 \
    OPENAI_BASE_URL=https://api.openai.com/v1 \
    ALLOWED_MODELS=gpt-4.1-mini \
    RATE_LIMIT_PER_MIN=30

EXPOSE 8080

# Healthy only once the key + app token are configured (via `fly secrets`).
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "--timeout", "60", "app:app"]
