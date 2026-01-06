# Инструкция по запуску в Docker

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose установлены
- Файл `moscow_buildings.csv` находится в корне проекта (или будет создан через preprocessing)

### Вариант 1: Запуск через Docker Compose (рекомендуется)

1. **Клонируйте репозиторий** (или используйте локальную копию):
   ```bash
   git clone <repository-url>
   cd best_hack
   ```

2. **Подготовьте данные** (если ещё не готовы):
   
   Если у вас уже есть `moscow_buildings.csv`:
   - Убедитесь, что файл находится в корне проекта
   
   Если нужно создать из PBF:
   ```bash
   # Поместите PBF файл в папку data/
   mkdir -p data
   # Скопируйте ваш PBF файл как data/data.osm.pbf
   
   # Запустите preprocessing (можно сделать локально или в контейнере)
   docker-compose run --rm geocoder-api python scripts/preprocessing.py
   ```

3. **Запустите сервис**:
   ```bash
   docker-compose up -d
   ```

4. **Проверьте работу**:
   ```bash
   # API должен быть доступен на http://localhost:8000
   curl "http://localhost:8000/geocode/improved?address=Москва, Тверская улица, 12"
   
   # Документация API
   # Откройте в браузере: http://localhost:8000/docs
   ```

5. **Остановите сервис**:
   ```bash
   docker-compose down
   ```

### Вариант 2: Запуск через Docker напрямую

1. **Соберите образ**:
   ```bash
   docker build -t moscow-geocoder .
   ```

2. **Запустите контейнер**:
   ```bash
   docker run -d \
     --name moscow-geocoder \
     -p 8000:8000 \
     -v $(pwd)/moscow_buildings.csv:/app/moscow_buildings.csv:ro \
     moscow-geocoder
   ```

3. **Проверьте логи**:
   ```bash
   docker logs moscow-geocoder
   ```

4. **Остановите контейнер**:
   ```bash
   docker stop moscow-geocoder
   docker rm moscow-geocoder
   ```

## Preprocessing в Docker

Если нужно выполнить preprocessing внутри Docker:

```bash
# Вариант 1: Через docker-compose
docker-compose run --rm geocoder-api python scripts/preprocessing.py

# Вариант 2: Через docker напрямую
docker run --rm \
  -v $(pwd)/data:/app/data:rw \
  -v $(pwd):/app:rw \
  moscow-geocoder \
  python scripts/preprocessing.py
```

## Troubleshooting

### Ошибка: файл moscow_buildings.csv не найден

Убедитесь, что файл существует и правильно смонтирован:
```bash
# Проверьте локальный файл
ls -lh moscow_buildings.csv

# Проверьте в контейнере
docker exec moscow-geocoder ls -lh /app/moscow_buildings.csv
```

### Порт 8000 уже занят

Измените порт в `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Теперь доступен на localhost:8080
```

### Ошибки при сборке (osmium)

Если возникают проблемы с установкой osmium, попробуйте использовать базовый образ с предустановленными зависимостями или соберите образ на машине с Linux.

## Локальный запуск без Docker

См. раздел "Установка и запуск" в основном README.md.



