FROM python:3.10-slim

# Install system dependencies needed for compiling python packages (like ChromaDB/onnx if wheels are missing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up the work directory
WORKDIR /app

# Copy the vendored local library (under the current context)
COPY mempalace /app/mempalace
RUN pip install --no-cache-dir /app/mempalace

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy django webapp files
COPY . /app/

# Create a data directory for persistent database storage (sqlite and mempalace)
RUN mkdir -p /data && chmod 777 /data

# Redirect home to /data so all local-first database/config files default to /data/.mempalace
ENV HOME=/data
ENV MEMPALACE_PALACE_PATH=/data/.mempalace/palace

# Expose port 8000
EXPOSE 8000

# Make start script executable
RUN chmod +x /app/start.sh

# Run the app
CMD ["/app/start.sh"]
