FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY dashboard.py .
COPY start.sh .

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/start.sh
USER appuser

EXPOSE 8000
EXPOSE 8501

CMD ["/bin/bash", "/app/start.sh"]
