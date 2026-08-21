FROM python:3.10-slim

WORKDIR /app

# Sistem bağımlılıkları (pandas/numpy için gerekli)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Port
EXPOSE 10000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
