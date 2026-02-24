# Alpha Copilot Social Agent Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium + system deps (needed for trade card image gen)
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Entrypoint picks post type based on UTC hour + day of week
CMD ["python", "entrypoint.py"]
