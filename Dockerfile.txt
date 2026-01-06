FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для osmium и shapely
RUN apt-get update && apt-get install -y \
    build-essential \
    libosmium2-dev \
    libbz2-dev \
    zlib1g-dev \
    libexpat1-dev \
    libboost-all-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём папку для данных
RUN mkdir -p data

# Указываем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# По умолчанию запускаем API
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]



