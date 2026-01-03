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

# Run agent with selective posting - only posts if compelling opportunity found
CMD ["python", "-m", "agent.main", "--task", "Check Alpha Copilot for compelling options opportunities. Only post to twitter if you find something genuinely worth sharing - high conviction plays with clear edge. If nothing stands out, call done without posting."]
