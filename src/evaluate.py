"""
Модуль оценки качества геокодеров.
"""

import math
import random
from typing import Dict, List, Tuple

import pandas as pd

from .data_loader import load_buildings_csv
from .normalize import add_normalized_columns, build_full_norm
from .geocode_basic import geocode_basic
from .geocode_improved import geocode_improved
from .config import EVALUATION_SAMPLE_SIZE


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Вычисляет расстояние Левенштейна между двумя строками.
    
    Args:
        s1: Первая строка
        s2: Вторая строка
        
    Returns:
        Расстояние Левенштейна
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Вычисляет расстояние по формуле Haversine между двумя точками на Земле.
    
    Args:
        lat1: Широта первой точки
        lon1: Долгота первой точки
        lat2: Широта второй точки
        lon2: Долгота второй точки
        
    Returns:
        Расстояние в метрах
    """
    # Радиус Земли в метрах
    R = 6371000
    
    # Преобразование в радианы
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Формула Haversine
    a = (
        math.sin(delta_phi / 2) ** 2 +
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def text_similarity_score(pred: str, true: str) -> float:
    """
    Вычисляет текстовый score схожести адресов.
    
    Args:
        pred: Предсказанный нормализованный адрес
        true: Истинный нормализованный адрес
        
    Returns:
        Score от 0 до 1
    """
    if not pred and not true:
        return 1.0
    
    if not pred or not true:
        return 0.0
    
    max_len = max(len(pred), len(true))
    if max_len == 0:
        return 1.0
    
    lev_dist = levenshtein_distance(pred, true)
    score = 1 - (lev_dist / max_len)
    return max(0.0, score)


def evaluate_single_query(
    query: str,
    true_city: str,
    true_street: str,
    true_number: str,
    true_lat: float,
    true_lon: float,
    true_full_norm: str
) -> Dict[str, any]:
    """
    Оценивает качество геокодирования для одного запроса.
    
    Args:
        query: Текст запроса
        true_city: Истинный город
        true_street: Истинная улица
        true_number: Истинный номер
        true_lat: Истинная широта
        true_lon: Истинная долгота
        true_full_norm: Истинный нормализованный адрес
        
    Returns:
        Словарь с метриками для basic и improved геокодеров
    """
    # Вызов базового геокодера
    res_basic = geocode_basic(query, limit=1)
    basic_obj = res_basic['objects'][0] if res_basic['objects'] else None
    
    # Вызов улучшенного геокодера
    res_improved = geocode_improved(query, limit=1)
    improved_obj = res_improved['objects'][0] if res_improved['objects'] else None
    
    # Обработка результатов basic
    if basic_obj:
        basic_pred_full_norm = build_full_norm(
            basic_obj['locality'],
            basic_obj['street'],
            basic_obj['number']
        )
        basic_text_score = text_similarity_score(basic_pred_full_norm, true_full_norm)
        basic_dist_m = haversine_distance(
            true_lat, true_lon,
            basic_obj['lat'], basic_obj['lon']
        )
    else:
        basic_pred_full_norm = ''
        basic_text_score = 0.0
        basic_dist_m = None
    
    # Обработка результатов improved
    if improved_obj:
        improved_pred_full_norm = build_full_norm(
            improved_obj['locality'],
            improved_obj['street'],
            improved_obj['number']
        )
        improved_text_score = text_similarity_score(improved_pred_full_norm, true_full_norm)
        improved_dist_m = haversine_distance(
            true_lat, true_lon,
            improved_obj['lat'], improved_obj['lon']
        )
    else:
        improved_pred_full_norm = ''
        improved_text_score = 0.0
        improved_dist_m = None
    
    return {
        'query': query,
        'true_full_norm': true_full_norm,
        'true_lat': true_lat,
        'true_lon': true_lon,
        'basic_pred_full_norm': basic_pred_full_norm,
        'basic_text_score': basic_text_score,
        'basic_dist_m': basic_dist_m,
        'improved_pred_full_norm': improved_pred_full_norm,
        'improved_text_score': improved_text_score,
        'improved_dist_m': improved_dist_m,
    }


def main():
    """
    Основная функция оценки качества.
    """
    print("Загрузка данных...")
    df = load_buildings_csv()
    df = add_normalized_columns(df)
    
    # Фильтруем строки, где есть хотя бы street
    df_filtered = df[df['street'].str.strip() != ''].copy()
    
    if len(df_filtered) == 0:
        print("Нет данных для оценки!")
        return
    
    # Выбираем случайные адреса
    sample_size = min(EVALUATION_SAMPLE_SIZE, len(df_filtered))
    df_sample = df_filtered.sample(n=sample_size, random_state=42)
    
    print(f"Оценка на {sample_size} примерах...")
    
    results = []
    
    for idx, (_, row) in enumerate(df_sample.iterrows(), 1):
        if idx % 50 == 0:
            print(f"Обработано {idx}/{sample_size}...")
        
        # Формируем запрос
        city = str(row['city']) if row['city'] else 'Москва'
        street = str(row['street'])
        number = str(row['housenumber'])
        query = f"{city}, {street} {number}".strip()
        
        # Оцениваем
        result = evaluate_single_query(
            query=query,
            true_city=str(row['city']),
            true_street=str(row['street']),
            true_number=str(row['housenumber']),
            true_lat=float(row['lat']),
            true_lon=float(row['lon']),
            true_full_norm=str(row['full_norm'])
        )
        
        results.append(result)
    
    # Сохраняем результаты
    results_df = pd.DataFrame(results)
    results_df.to_csv('evaluation_results.csv', index=False, encoding='utf-8')
    print(f"\nРезультаты сохранены в evaluation_results.csv")
    
    # Вычисляем агрегированные метрики
    print("\n" + "="*60)
    print("АГРЕГИРОВАННЫЕ МЕТРИКИ")
    print("="*60)
    
    # Текстовые score
    print("\nТекстовые метрики (score 0-1, где 1 = полное совпадение):")
    print(f"  Basic:")
    print(f"    Средний: {results_df['basic_text_score'].mean():.4f}")
    print(f"    Медианный: {results_df['basic_text_score'].median():.4f}")
    print(f"  Improved:")
    print(f"    Средний: {results_df['improved_text_score'].mean():.4f}")
    print(f"    Медианный: {results_df['improved_text_score'].median():.4f}")
    
    # Геодистанции (только для успешных предсказаний)
    basic_dists = results_df['basic_dist_m'].dropna()
    improved_dists = results_df['improved_dist_m'].dropna()
    
    print("\nГеодистанции (метры):")
    print(f"  Basic:")
    if len(basic_dists) > 0:
        print(f"    Средняя: {basic_dists.mean():.2f}")
        print(f"    Медианная: {basic_dists.median():.2f}")
        print(f"    Успешных предсказаний: {len(basic_dists)}/{len(results_df)}")
    else:
        print(f"    Нет успешных предсказаний")
    
    print(f"  Improved:")
    if len(improved_dists) > 0:
        print(f"    Средняя: {improved_dists.mean():.2f}")
        print(f"    Медианная: {improved_dists.median():.2f}")
        print(f"    Успешных предсказаний: {len(improved_dists)}/{len(results_df)}")
    else:
        print(f"    Нет успешных предсказаний")
    
    print("\n" + "="*60)

