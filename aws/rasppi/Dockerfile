# Use Python 3.11 as it's more stable for production
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcamera0 \
    python3-libcamera \
    python3-kms++ \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create directory for temporary files
RUN mkdir -p /tmp/nutrition_results

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_ACCESS_KEY_ID=your_access_key_id
ENV AWS_SECRET_ACCESS_KEY=your_secret_access_key
ENV OPENAI_API_KEY=your_openai_api_key
ENV NUTRITIONIX_APP_ID=your_nutritionix_app_id
ENV NUTRITIONIX_API_KEY=your_nutritionix_api_key
ENV S3_BUCKET_NAME=your_bucket_name
ENV AWS_REGION=us-east-1

# Run the application
CMD ["python", "app.py"]