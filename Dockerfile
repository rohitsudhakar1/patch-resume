FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tectonic \
    tesseract-ocr \
    tesseract-ocr-eng \
    synctex \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY . .

# Create storage directory
RUN mkdir -p storage

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
