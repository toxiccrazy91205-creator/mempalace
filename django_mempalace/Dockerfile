FROM python:3.10-slim

# Install system dependencies needed for compiling python packages (like ChromaDB/onnx if wheels are missing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up the work directory
WORKDIR /app

# Copy and install the local mempalace package first (incorporating local fixes)
COPY mempalace /app/mempalace
RUN pip install --no-cache-dir /app/mempalace

# Copy django webapp requirements
COPY django_mempalace/requirements.txt /app/django_mempalace/
RUN pip install --no-cache-dir -r /app/django_mempalace/requirements.txt

# Copy the rest of the django webapp files
COPY django_mempalace /app/django_mempalace

# Create a data directory for persistent database storage (sqlite and mempalace)
RUN mkdir -p /data && chmod 777 /data

# Redirect home to /data so all local-first database/config files default to /data/.mempalace
ENV HOME=/data
ENV MEMPALACE_PALACE_PATH=/data/.mempalace/palace

WORKDIR /app/django_mempalace

# Expose port 8000
EXPOSE 8000

# Make start script executable
RUN chmod +x /app/django_mempalace/start.sh

# Run the app
CMD ["/app/django_mempalace/start.sh"]
