# Краткая инструкция по размещению проекта на GitHub

## Быстрый старт (5 минут)

### 1. Создайте репозиторий на GitHub

1. Перейдите на https://github.com
2. Нажмите **"New"** (или **"+"** → **"New repository"**)
3. Заполните:
   - **Repository name**: `moscow-geocoder` (или любое другое имя)
   - **Description**: "Геокодер адресов Москвы по данным OpenStreetMap"
   - **Visibility**: Public или Private (на ваш выбор)
   - ❌ **НЕ ставьте галочки** на "Initialize with README", "Add .gitignore", "Add license"
4. Нажмите **"Create repository"**

### 2. Инициализируйте Git в локальной папке

Откройте терминал в папке проекта (`best_hack`) и выполните:

```bash
# 1. Инициализируйте git репозиторий
git init

# 2. Добавьте все файлы
git add .

# 3. Сделайте первый коммит
git commit -m "Initial commit: геокодер адресов Москвы"

# 4. Переименуйте ветку в main (если нужно)
git branch -M main
```

### 3. Подключите к GitHub

GitHub покажет вам команды после создания репозитория. Выполните:

```bash
# Замените <your-username> и <repository-name> на ваши данные
git remote add origin https://github.com/<your-username>/<repository-name>.git

# Отправьте код на GitHub
git push -u origin main
```

### 4. Готово! ✅

Ваш проект теперь на GitHub. Перейдите на страницу репозитория, чтобы убедиться.

## Важные файлы (уже готовы)

- ✅ `.gitignore` — исключает ненужные файлы (кэш, большие CSV)
- ✅ `README.md` — полная документация проекта
- ✅ `Dockerfile` и `docker-compose.yml` — для запуска в Docker
- ✅ Все исходные файлы

## Что НЕ будет в репозитории

Благодаря `.gitignore`, следующие файлы **не попадут** в репозиторий:
- ❌ `moscow_buildings.csv` — большие данные (можно добавить позже, если нужно)
- ❌ `data/*.pbf` — исходные PBF файлы
- ❌ `__pycache__/` — кэш Python
- ❌ `*.csv` (кроме requirements.txt)
- ❌ Результаты оценки (`evaluation_results.csv`)

## Если нужно добавить данные в репозиторий

Если вы хотите включить `moscow_buildings.csv` (например, для удобства судей):

```bash
# 1. Проверьте размер файла (GitHub лимит: 100MB на файл)
# Если файл больше 100MB, используйте Git LFS или не добавляйте

# 2. Временно отредактируйте .gitignore
# Закомментируйте строку с "*.csv" или добавьте исключение:
# !moscow_buildings.csv

# 3. Добавьте файл явно
git add -f moscow_buildings.csv

# 4. Закоммитьте
git commit -m "Add prepared data file"

# 5. Отправьте на GitHub
git push
```

## Последующие изменения

Когда вы делаете изменения в коде:

```bash
# 1. Посмотрите, что изменилось
git status

# 2. Добавьте изменения
git add .

# 3. Закоммитьте
git commit -m "Описание изменений"

# 4. Отправьте на GitHub
git push
```

## Проверка перед публикацией

1. ✅ Убедитесь, что `moscow_buildings.csv` есть в `.gitignore` (если не хотите его включать)
2. ✅ Проверьте, что все нужные файлы добавлены: `git status`
3. ✅ Убедитесь, что README читаем и понятен

## Ссылки для проверки

После публикации проверьте:
- README отображается корректно
- Все файлы видны
- Docker конфигурация на месте

## Troubleshooting

### Ошибка: "large files detected"

Если GitHub жалуется на большие файлы:
```bash
# Удалите файл из истории (если уже закоммитили)
git rm --cached moscow_buildings.csv
git commit -m "Remove large data file"

# Или используйте Git LFS для больших файлов
git lfs install
git lfs track "*.csv"
git add .gitattributes
```

### Ошибка: "authentication failed"

Настройте аутентификацию:
- Используйте Personal Access Token (вместо пароля)
- Или настройте SSH ключи

### Изменить remote URL

```bash
# Посмотреть текущий remote
git remote -v

# Изменить URL
git remote set-url origin <new-url>
```

