FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

# Install system build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application codebase
COPY . .

# Expose Streamlit (8501) and FastAPI (8000)
EXPOSE 8501 8000

# Default command launches the interactive Streamlit Dashboard
CMD ["streamlit", "run", "frontend/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
