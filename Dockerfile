# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory exactly to /app
WORKDIR /app

# Install critical system libraries required by OSMnx/Geopandas (libspatialindex)
# This prevents the container from crashing when importing routing files!
RUN apt-get update && apt-get install -y \
    libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies (And forcefully ensure gunicorn is installed for web serving)
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy all the rest of your application code
COPY . .

# Hugging Face MUST use port 7860 natively. Do not change this to 8080.
EXPOSE 7860

# Run the Gunicorn web server targeting Hugging Face's exact port constraint
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "2", "--timeout", "120"]
