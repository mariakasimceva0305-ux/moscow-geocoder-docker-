"""
Конфигурация проекта.
"""

import os
from pathlib import Path

# Путь к исходным данным
DATA_PATH = Path(__file__).parent.parent / "moscow_buildings.csv"

# Флаги использования базы данных.
# По умолчанию БД выключена, чтобы локальный запуск работал "из коробки"
# только с CSV-файлом `moscow_buildings.csv`.
USE_DATABASE: bool = os.getenv("USE_DATABASE", "false").lower() in {"1", "true", "yes"}

# Если где‑то нужно явно указать использование SQLite вместо PostgreSQL,
# можно задать переменную окружения USE_SQLITE=true.
USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() in {"1", "true", "yes"}

# Параметры для improved геокодера
FUZZY_MATCH_MIN_SCORE = 0.6
FUZZY_TOP_K = 15  # Увеличиваем для большего охвата
HOUSE_NUMBER_DISTANCE_BETA = 3.0  # Уменьшаем для более резкого падения score при различиях
SCORE_STREET_WEIGHT = 0.25  # Вес улицы, если номер не указан
SCORE_NUMBER_WEIGHT = 0.75  # Вес номера, если номер не указан
# Если номер указан: используются адаптивные веса в зависимости от похожести улицы

# Параметры для оценки
EVALUATION_SAMPLE_SIZE = 500

