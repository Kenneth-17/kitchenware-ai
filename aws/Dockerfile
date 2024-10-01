# Use a base image that works on both PC and Raspberry Pi
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create app directory
WORKDIR /app

# Copy your Python script
COPY food_analyzer.py .

# Create directory for AWS credentials
RUN mkdir -p /root/.aws

# Run script
CMD ["python", "food_analyzer.py"]