# Use official Python 3.12 slim image for a lightweight container footprint
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency definition file first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip and install backend Python dependencies without caching wheel files
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code into the container
COPY app ./app

# Expose container port 8000
EXPOSE 8000

# Execute Uvicorn server binding to 0.0.0.0 on port 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
