# Инструкция по настройке Git репозитория

## Быстрая инициализация

```bash
# 1. Инициализируйте git репозиторий
git init

# 2. Добавьте все файлы (кроме тех, что в .gitignore)
git add .

# 3. Сделайте первый коммит
git commit -m "Initial commit: геокодер адресов Москвы"

# 4. (Опционально) Создайте репозиторий на GitHub и добавьте remote
git remote add origin <your-repository-url>
git branch -M main
git push -u origin main
```

## Что будет в репозитории

✅ **Включается:**
- Весь исходный код (`src/`, `scripts/`)
- Конфигурационные файлы (`requirements.txt`, `Dockerfile`, `docker-compose.yml`)
- Документация (`README.md`, `DOCKER.md`, `SCORE_EXPLANATION.md`)
- Структура проекта

❌ **Исключается (через .gitignore):**
- `moscow_buildings.csv` — большие данные (можно добавить отдельно, если нужно)
- `data/*.pbf` — исходные PBF файлы
- `__pycache__/` — кэш Python
- `*.csv` — результаты оценки (кроме requirements.txt)
- Виртуальные окружения
- IDE файлы

## Если нужно включить данные в репозиторий

Если вы хотите включить `moscow_buildings.csv` в репозиторий (для удобства судей):

```bash
# 1. Временно удалите moscow_buildings.csv из .gitignore
# Отредактируйте .gitignore и закомментируйте строку "*.csv"

# 2. Добавьте файл явно
git add -f moscow_buildings.csv

# 3. Закоммитьте
git commit -m "Add prepared data file"
```

> **Примечание:** CSV файл может быть большим (десятки-сотни MB). GitHub имеет лимит 100MB на файл. Если файл больше, используйте Git LFS или оставьте инструкцию по подготовке данных.

## Рекомендуемая структура коммитов

```bash
git commit -m "feat: add baseline geocoder"
git commit -m "feat: add improved geocoder with fuzzy search"
git commit -m "feat: add preprocessing script for PBF files"
git commit -m "docs: add comprehensive README and Docker instructions"
git commit -m "feat: add Docker support"
```



