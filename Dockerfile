FROM python:3.12-slim

# Install Tesseract OCR (the actual binary pytesseract calls out to)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project
COPY . .

# Render sets $PORT at runtime; Flask must bind to it
ENV PORT=10000
EXPOSE 10000

CMD ["python", "app.py"]