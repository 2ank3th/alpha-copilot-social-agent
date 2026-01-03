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

# Run agent - research market trends, form thesis, find options, post if compelling
CMD ["python", "-m", "agent.main", "--task", "Research today's market trends to find a compelling trading idea. Form a thesis (what stock, why bullish/bearish, what catalyst). Use Alpha Copilot to find options matching your thesis. Post to twitter only if the idea is genuinely interesting. If nothing stands out, call done without posting."]
