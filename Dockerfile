# Alpha Copilot Social Agent Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Default command - can be overridden
CMD ["python", "-m", "agent.main", "--help"]
