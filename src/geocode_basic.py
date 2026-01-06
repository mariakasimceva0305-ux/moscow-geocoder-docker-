"""
Базовый геокодер (baseline).
Точное сопоставление по нормализованным полям.
"""

import pandas as pd
from typing import Dict, List, Any, Optional

from .config import USE_DATABASE, DATA_PATH
from .data_loader import load_buildings_csv
from .normalize import (
    norm_city,
    norm_street,
    norm_number,
    add_normalized_columns,
    build_full_norm
)

# Глобальный кэш данных
_cached_df: pd.DataFrame | None = None
_db_available: Optional[bool] = None


def _check_db_available() -> bool:
    """Проверяет, доступна ли база данных."""
    global _db_available
    if _db_available is not None:
        return _db_available
    
    if not USE_DATABASE:
        _db_available = False
        return False
    
    try:
        from .database import get_engine, _table_name, USE_SQLITE
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            # Проверяем существование таблицы (разные запросы для SQLite и PostgreSQL)
            if USE_SQLITE:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
                ), {"name": _table_name})
            else:
                result = conn.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename=:name"
                ), {"name": _table_name})
            _db_available = result.fetchone() is not None
        return _db_available
    except Exception as e:
        # База данных недоступна - это нормально, будет использоваться CSV
        _db_available = False
        return False


def _get_cached_data() -> pd.DataFrame:
    """
    Загружает и кэширует нормализованные данные.
    
    Приоритет:
    1. Если USE_DATABASE=True и БД доступна - загружает из БД (быстрее с индексами)
    2. Иначе - загружает из CSV и нормализует
    """
    global _cached_df
    if _cached_df is not None:
        return _cached_df
    
    # Пробуем загрузить из БД если доступна
    if _check_db_available():
        try:
            from .database import load_from_db
            print("Загрузка данных из базы данных...")
            _cached_df = load_from_db()
            print(f"[OK] Загружено {len(_cached_df)} записей из БД")
            return _cached_df
        except Exception as e:
            print(f"Ошибка загрузки из БД, используем CSV: {e}")
    
    # Fallback на CSV
    print("Загрузка данных из CSV...")
    df = load_buildings_csv()
    print(f"Загружено {len(df)} записей. Нормализация...")
    _cached_df = add_normalized_columns(df)
    print(f"[OK] Нормализация завершена. Всего записей: {len(_cached_df)}")
    return _cached_df


def geocode_basic(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Baseline-геокодер:
      1) парсит строку "город, улица, номер" по запятым,
      2) нормализует компоненты (norm_city/norm_street/norm_number),
      3) делает точный фильтр по нормализованным колонкам,
      4) возвращает топ-N совпадений в формате JSON из условия.
    
    Args:
        query: Строка запроса (например, "Москва, Тверская улица, 12к1")
        limit: Максимальное количество результатов
        
    Returns:
        Словарь с ключами:
        - searched_address: исходный запрос
        - objects: список найденных объектов
    """
    # Парсинг запроса
    parts = [p.strip() for p in query.split(',')]
    
    city_raw = parts[0] if len(parts) > 0 else ''
    street_raw = parts[1] if len(parts) > 1 else ''
    number_raw = parts[2] if len(parts) > 2 else ''
    
    # Нормализация
    city_norm = norm_city(city_raw)
    street_norm = norm_street(street_raw)
    number_norm = norm_number(number_raw)
    
    # Пробуем использовать БД для точного поиска (быстрее с индексами)
    use_db_results = False
    if _check_db_available():
        try:
            from .database import search_by_norm
            results_df = search_by_norm(
                city_norm=city_norm if city_norm else None,
                street_norm=street_norm if street_norm else None,
                number_norm=number_norm if number_norm else None,
                limit=limit
            )
            # Если результаты найдены в БД - используем их
            if len(results_df) > 0:
                use_db_results = True
        except Exception as e:
            # Если ошибка БД - fallback на обычный поиск
            print(f"Ошибка поиска в БД, используем CSV: {e}")
            use_db_results = False
    
    # Если БД недоступна или поиск не дал результатов - используем pandas
    if not use_db_results:
        df = _get_cached_data()
        # Фильтрация
        mask = pd.Series(True, index=df.index)
        if city_norm:
            mask = mask & (df['city_norm'] == city_norm)
        if street_norm:
            mask = mask & (df['street_norm'] == street_norm)
        if number_norm:
            mask = mask & (df['number_norm'] == number_norm)
        results_df = df[mask].head(limit)
    
    # Формирование ответа
    objects = []
    for _, row in results_df.iterrows():
        # Собираем нормализованный адрес в формате организаторов
        city_val = str(row['city']) if row.get('city') else ''
        street_val = str(row['street']) if row.get('street') else ''
        number_val = str(row['housenumber']) if row.get('housenumber') else ''
        
        # Нормализуем для формирования полного адреса
        city_norm_val = norm_city(city_val) if city_val else 'москва'
        street_norm_val = norm_street(street_val) if street_val else ''
        number_norm_val = norm_number(number_val) if number_val else ''
        
        # Формируем нормализованный адрес в требуемом формате
        normalized_address = build_full_norm(
            city_norm_val, 
            street_norm_val, 
            number_norm_val, 
            for_display=True
        ) if street_norm_val else ''
        
        objects.append({
            "locality": city_val,
            "street": street_val,
            "number": number_val,
            "normalized_address": normalized_address,  # Нормализованный адрес в формате организаторов
            "lon": float(row['lon']),
            "lat": float(row['lat']),
            "score": 1.0  # Для baseline всегда 1.0
        })
    
    return {
        "searched_address": query,
        "objects": objects
    }

