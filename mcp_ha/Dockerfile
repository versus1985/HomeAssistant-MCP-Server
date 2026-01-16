FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY config.yaml .
COPY run.sh .
RUN chmod +x run.sh

# Expose port
EXPOSE 8099

# Run the server
CMD ["./run.sh"]
