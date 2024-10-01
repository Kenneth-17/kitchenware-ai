# Use a base image that works on both PC and Raspberry Pi
FROM python:3.9-slim

# Install build tools and dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clone and build Raspberry Pi userland libraries
RUN git clone https://github.com/raspberrypi/userland.git /opt/userland && \
    cd /opt/userland && \
    ./buildme && \
    cp build/*/*.so /usr/local/lib/ && \
    cp build/*/*.so.* /usr/local/lib/ && \
    ldconfig

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