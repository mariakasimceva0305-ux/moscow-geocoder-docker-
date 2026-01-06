"""
Модуль для загрузки данных о зданиях Москвы.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import DATA_PATH


@dataclass
class BuildingRecord:
    """Запись о здании."""
    osm_id: int | str
    city: str
    street: str
    housenumber: str
    lon: float
    lat: float
    # Нормализованные поля (будут добавлены позже)
    city_norm: Optional[str] = None
    street_norm: Optional[str] = None
    number_norm: Optional[str] = None
    full_norm: Optional[str] = None


def load_buildings_csv(path: str | Path = None) -> pd.DataFrame:
    """
    Загружает CSV с зданиями Москвы и возвращает DataFrame.
    
    Приводит колонки к стандартным именам:
    - osm_id, city, street, housenumber, lon, lat
    
    Args:
        path: Путь к CSV файлу. Если None, используется DATA_PATH из config.
        
    Returns:
        DataFrame с нормализованными колонками.
    """
    if path is None:
        path = DATA_PATH
    
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл данных не найден: {path}")
    
    df = pd.read_csv(path)
    
    # Проверяем наличие необходимых колонок
    required_cols = ['osm_id', 'city', 'street', 'housenumber', 'lon', 'lat']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Отсутствуют необходимые колонки: {missing_cols}")
    
    # Приводим к стандартным типам
    df['osm_id'] = df['osm_id'].astype(str)
    df['city'] = df['city'].fillna('').astype(str)
    df['street'] = df['street'].fillna('').astype(str)
    df['housenumber'] = df['housenumber'].fillna('').astype(str)
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    
    # Удаляем строки с некорректными координатами
    df = df.dropna(subset=['lon', 'lat'])
    
    return df

