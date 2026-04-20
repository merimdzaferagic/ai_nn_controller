FROM python:3.11-slim

WORKDIR /app

# Install dependencies and curl
RUN apt-get update && apt-get install -y curl iputils-ping
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy client files
COPY client.py .
COPY examples.py .
COPY cli.py .

# Make scripts executable
RUN chmod +x examples.py cli.py

# Default command: run interactive CLI
CMD ["python3", "cli.py"]
