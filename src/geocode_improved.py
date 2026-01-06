"""
Улучшенный геокодер с фуззи-поиском и умным скорингом.
"""

import math
import re
from typing import Dict, List, Any

import pandas as pd
from rapidfuzz import fuzz, process

from .data_loader import load_buildings_csv
from .normalize import (
    norm_city,
    norm_street,
    norm_number,
    parse_house_number_full,
    add_normalized_columns,
    build_full_norm,
    HouseNumberParsed
)
from .config import (
    FUZZY_MATCH_MIN_SCORE,
    FUZZY_TOP_K,
    HOUSE_NUMBER_DISTANCE_BETA,
    SCORE_STREET_WEIGHT,
    SCORE_NUMBER_WEIGHT,
    USE_DATABASE
)

# Глобальный кэш данных
_cached_df: pd.DataFrame | None = None


def _get_cached_data() -> pd.DataFrame:
    """
    Загружает и кэширует нормализованные данные.
    
    Использует тот же кэш, что и базовый геокодер (если данные уже загружены).
    Для fuzzy поиска нужны все данные в памяти (pandas), поэтому используем общий кэш.
    """
    global _cached_df
    if _cached_df is not None:
        return _cached_df
    
    # Пытаемся использовать кэш из базового геокодера (если он уже загружен)
    try:
        from .geocode_basic import _cached_df as basic_cached_df, _get_cached_data as basic_get_data
        if basic_cached_df is not None:
            _cached_df = basic_cached_df
            return _cached_df
        else:
            # Используем функцию загрузки из базового геокодера (она сама решит БД или CSV)
            _cached_df = basic_get_data()
            return _cached_df
    except:
        pass
    
    # Fallback: если базовый геокодер не загружен, используем БД если доступна
    if USE_DATABASE:
        try:
            from .database import load_from_db
            _cached_df = load_from_db()
            return _cached_df
        except:
            pass
    
    # Последний fallback: CSV
    df = load_buildings_csv()
    _cached_df = add_normalized_columns(df)
    return _cached_df


def parse_address(query: str) -> tuple[str, str, str]:
    """
    Парсит адресный запрос на компоненты.
    
    Возвращает (city_raw, street_raw, number_raw).
    1) Делим по запятым.
    2) Если первая часть содержит 'моск', считаем это городом.
    3) Остальное — улица и номер.
    4) Если номер не выделен, пытаемся отделить номер дома от улицы.
       Номер дома может состоять из нескольких токенов: "14", "14 с1", "12к1", и т.д.
    
    Args:
        query: Строка запроса
        
    Returns:
        Кортеж (city_raw, street_raw, number_raw)
    """
    parts = [p.strip() for p in query.split(',')]
    
    city_raw = ''
    street_raw = ''
    number_raw = ''
    
    # Определяем город (первая часть или первая часть с "моск")
    if parts:
        first_part = parts[0].lower()
        if 'моск' in first_part:
            city_raw = parts[0]
            remaining = parts[1:] if len(parts) > 1 else []
        else:
            # Может быть город не указан, тогда первая часть - улица
            remaining = parts
    else:
        remaining = []
    
    # Остальное - улица и номер
    if remaining:
        street_part = remaining[0]
        
        # Пытаемся выделить номер дома из строки улицы
        # Номер дома может быть: "14", "14 с1", "12к1", "12/1", "23/19", и т.д.
        # Ищем паттерн номера дома в конце строки
        
        tokens = street_part.split()
        
        # Паттерн для номера дома: может начинаться с цифры и содержать:
        # - только цифры: "14"
        # - цифры + буквы/сокращения: "14с1", "12к1", "12А"
        # - дробь: "12/1", "23/19"
        # - несколько токенов: "14 с1", "12 корп 1"
        
        # Ищем с конца последовательность токенов, которая похожа на номер дома
        # Паттерн: "14 с1", "12к1", "23/19", "12 корпус 1"
        
        number_tokens = []
        number_start_idx = None
        
        # Идём с конца и собираем токены, которые являются частью номера
        # Номер дома может состоять из:
        # - цифр: "14"
        # - цифр + букв: "14с1", "12к1", "12А"
        # - нескольких токенов: "14 с1", "12 корпус 1"
        
        i = len(tokens) - 1
        found_digit_token = False
        
        while i >= 0 and len(number_tokens) < 4:  # Ограничиваем длину номера
            token = tokens[i]
            token_lower = token.lower()
            
            # Проверяем, является ли токен частью номера дома
            is_number_part = False
            
            # 1. Токен с цифрами - основная часть номера
            if re.search(r'\d', token):
                is_number_part = True
                found_digit_token = True
                number_start_idx = i
            # 2. Короткие сокращения (после цифр): с, к, стр, корп
            elif found_digit_token and len(token_lower) <= 4:
                if token_lower in ['с', 'к', 'корп', 'стр', 'корпус', 'строение', 'литер', 'лит']:
                    is_number_part = True
            # 3. Одна буква (литера): а, б, в, г...
            elif found_digit_token and len(token_lower) == 1 and re.match(r'^[а-яёa-z]$', token_lower):
                is_number_part = True
            
            if is_number_part:
                number_tokens.insert(0, token)
                i -= 1
            elif found_digit_token:
                # Если уже нашли цифру, но текущий токен не похож на номер - останавливаемся
                break
            else:
                # Если ещё не нашли цифру, продолжаем поиск
                i -= 1
        
        if number_start_idx is not None:
            # Разделяем на улицу и номер
            street_raw = ' '.join(tokens[:number_start_idx])
            number_raw = ' '.join(number_tokens)
        else:
            street_raw = street_part
        
        # Если есть вторая часть после запятой - это может быть номер
        if len(remaining) > 1:
            if number_raw:
                # Объединяем номера, если оба найдены
                number_raw = number_raw + ' ' + remaining[1]
            else:
                number_raw = remaining[1]
    
    return city_raw, street_raw, number_raw


def house_number_distance(q: HouseNumberParsed, c: HouseNumberParsed) -> float:
    """
    Вычисляет числовую "дистанцию" между номерами домов.
    
    Улучшенная версия:
    - Если base отличается, штраф нелинейный (логарифмический для небольших различий)
    - Более мягкие штрафы за отсутствие опциональных компонентов (corpus, building)
    - Полное совпадение = 0
    
    Args:
        q: Номер из запроса
        c: Номер кандидата
        
    Returns:
        Числовая дистанция
    """
    distance = 0.0
    
    # Основной номер - самый важный
    if q.base is not None and c.base is not None:
        base_diff = abs(q.base - c.base)
        if base_diff == 0:
            distance += 0  # Полное совпадение
        elif base_diff == 1:
            distance += 5  # Соседние дома - небольшой штраф
        else:
            # Для больших различий - линейный штраф
            distance += 10 + 5 * base_diff
    elif q.base is not None or c.base is not None:
        # Если один есть, а другого нет - очень большой штраф
        distance += 200
    
    # Корпус - важный, но не критичный
    if q.corpus is not None and c.corpus is not None:
        distance += 5 * abs(q.corpus - c.corpus)
    elif q.corpus is not None or c.corpus is not None:
        # Если запрос имеет корпус, а кандидат нет - штраф
        if q.corpus is not None:
            distance += 30  # Запрошен корпус, но его нет
        else:
            distance += 5  # Корпус есть, но не запрашивался (меньший штраф)
    
    # Строение - менее важное
    if q.building is not None and c.building is not None:
        distance += 3 * abs(q.building - c.building)
    elif q.building is not None or c.building is not None:
        # Если запрос имеет строение, а кандидат нет - штраф
        if q.building is not None:
            distance += 20  # Запрошено строение, но его нет
        else:
            # Строение есть, но не запрашивалось - это нормально (пользователь может не указать)
            # Если base совпадает, строение не должно сильно снижать score
            if q.base is not None and c.base is not None and q.base == c.base:
                # Base совпадает - строение не критично
                distance += 3  # Минимальный штраф
            else:
                distance += 8  # Обычный штраф для строений
    
    # Литера - наименее важная
    if q.letter is not None and c.letter is not None:
        if q.letter != c.letter:
            distance += 2
    elif q.letter is not None or c.letter is not None:
        # Если запрос имеет литеру, а кандидат нет - небольшой штраф
        if q.letter is not None:
            distance += 10
        else:
            distance += 1
    
    return distance


def _decompose_street(street_norm: str) -> Dict[str, Any]:
    """
    Разбирает нормализованную улицу на компоненты:
    - прилагательное (если есть)
    - "ядро" названия
    - тип улицы
    """
    if not street_norm:
        return {
            "street_norm": "",
            "street_core": "",
            "street_adj": None,
            "street_type": None,
        }

    tokens = street_norm.split()
    if not tokens:
        return {
            "street_norm": street_norm,
            "street_core": street_norm,
            "street_adj": None,
            "street_type": None,
        }

    # Возможные типы улиц (должны совпадать с normalize.STREET_TYPE_MAP)
    street_types = {
        "улица",
        "проспект",
        "проезд",
        "переулок",
        "бульвар",
        "шоссе",
        "набережная",
        "площадь",
        "аллея",
        "тупик",
    }

    street_type = None
    if tokens[-1] in street_types:
        street_type = tokens[-1]
        tokens = tokens[:-1]

    street_adj = None
    if tokens and tokens[0] in {"большая", "малая", "новая", "старая"}:
        street_adj = tokens[0]
        tokens = tokens[1:]

    street_core = " ".join(tokens) if tokens else ""

    return {
        "street_norm": street_norm,
        "street_core": street_core,
        "street_adj": street_adj,
        "street_type": street_type,
    }


def geocode_improved_fuzzy_only(
    query: str,
    limit: int = 5,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Улучшенный геокодер с фуззи-поиском и умным скорингом (без предварительного baseline).
    
    Используется внутренне после попытки baseline.
    
    Алгоритм:
    1. Парсинг запроса на компоненты
    2. Нормализация компонентов
    3. Фильтрация по городу
    4. Фуззи-поиск по улице
    5. Умное сравнение номеров домов
    6. Финальный score и сортировка
    
    Args:
        query: Строка запроса
        limit: Максимальное количество результатов
        
    Returns:
        Словарь с результатами геокодирования
    """
    # 1. Парсинг запроса
    city_raw, street_raw, number_raw = parse_address(query)
    
    # 2. Нормализация
    q_city_norm = norm_city(city_raw) if city_raw else "москва"
    q_street_norm = norm_street(street_raw)
    q_number_norm = norm_number(number_raw)
    
    # 3. Парсинг номера дома
    q_number_parsed = parse_house_number_full(q_number_norm)
    
    # 4. Загрузка данных
    df = _get_cached_data()
    
    # 5. Фильтрация по городу
    if q_city_norm:
        df_filtered = df[df["city_norm"] == q_city_norm].copy()
    else:
        df_filtered = df.copy()
    
    if df_filtered.empty:
        return {
            "searched_address": query,
            "objects": []
        }
    
    # 6. Двухшаговый выбор: сначала выбираем лучшую улицу
    # Вариант 1: Выбираем топ-1 или топ-2 улицы с максимальной похожестью
    unique_streets = df_filtered["street_norm"].unique().tolist()
    
    if q_street_norm and unique_streets:
        # Находим топ-K похожих улиц
        street_matches = process.extract(
            q_street_norm,
            unique_streets,
            scorer=fuzz.QRatio,
            limit=FUZZY_TOP_K
        )
        
        # Двухшаговый выбор: берём только топ-1 или топ-2 лучшие улицы
        # Если лучшая улица сильно лучше второй (разница > 5%), берём только её
        # Иначе берём топ-2 для безопасности
        
        if len(street_matches) > 0:
            best_street, best_score, _ = street_matches[0]
            
            # Проверяем, есть ли вторая улица и насколько она хуже
            if len(street_matches) > 1:
                second_street, second_score, _ = street_matches[1]
                score_diff = best_score - second_score
                
                # Если лучшая улица намного лучше (> 5%), берём только её
                if score_diff > 5 and best_score >= FUZZY_MATCH_MIN_SCORE * 100:
                    matching_streets = [best_street]
                # Если две лучшие улицы близки по score, берём обе (но не более 2)
                elif best_score >= FUZZY_MATCH_MIN_SCORE * 100:
                    matching_streets = [
                        street for street, score, _ in street_matches[:2]
                        if score >= FUZZY_MATCH_MIN_SCORE * 100
                    ]
                else:
                    matching_streets = []
            else:
                # Только одна улица найдена
                if best_score >= FUZZY_MATCH_MIN_SCORE * 100:
                    matching_streets = [best_street]
                else:
                    matching_streets = []
        else:
            matching_streets = []
        
        # Создаём словарь для быстрого доступа к score
        street_scores_dict = {
            street: score / 100.0  # нормализуем к 0-1
            for street, score, _ in street_matches
        }
        
        if matching_streets:
            # Фильтруем по найденным улицам (теперь их максимум 1-2)
            df_filtered = df_filtered[df_filtered["street_norm"].isin(matching_streets)].copy()
            # Добавляем score похожести улицы
            df_filtered["street_sim"] = df_filtered["street_norm"].map(street_scores_dict)
        else:
            # Если нет похожих улиц, возвращаем пустой результат
            return {
                "searched_address": query,
                "objects": []
            }
    else:
        # Если улица не указана, считаем score = 0.5
        df_filtered["street_sim"] = 0.5
    
    if df_filtered.empty:
        return {
            "searched_address": query,
            "objects": []
        }
    
    # 7. Сравнение номеров домов
    number_scores: list[float] = []
    number_distances: list[float] = []
    
    # Проверяем, указан ли номер дома в запросе
    has_number_in_query = q_number_parsed.base is not None
    
    for _, row in df_filtered.iterrows():
        c_number_norm = row["number_norm"]
        c_number_parsed = parse_house_number_full(c_number_norm)
        
        # Вычисляем дистанцию
        dist = house_number_distance(q_number_parsed, c_number_parsed)
        
        # Преобразуем в score (экспоненциальное убывание)
        if dist == 0:
            num_score = 1.0  # Полное совпадение
        else:
            num_score = math.exp(-dist / HOUSE_NUMBER_DISTANCE_BETA)
        
        # Если номер дома указан в запросе и есть точное совпадение,
        # даём бонус к score улицы (для повышения приоритета точных совпадений)
        if has_number_in_query and dist == 0:
            # Точное совпадение номера увеличивает вес результата
            num_score = 1.0
        
        number_scores.append(num_score)
        number_distances.append(dist)
    
    df_filtered["number_score"] = number_scores
    df_filtered["number_distance"] = number_distances
    
    # 8. Финальный score
    # Адаптивные веса в зависимости от ситуации
    if has_number_in_query:
        # Когда номер указан, используем адаптивные веса:
        # - Если улица очень похожа (>= 0.85), даём ей больше веса
        # - Иначе номер остаётся приоритетным
        
        # Вычисляем среднюю похожесть улиц в результатах
        avg_street_sim = df_filtered["street_sim"].mean() if len(df_filtered) > 0 else 0.0
        
        # Если улицы очень похожи, балансируем веса
        if avg_street_sim >= 0.85:
            # Высокая похожесть улиц - даём улице больший вес
            street_weight = 0.4
            number_weight = 0.6
        elif avg_street_sim >= 0.7:
            # Средняя похожесть - баланс
            street_weight = 0.3
            number_weight = 0.7
        else:
            # Низкая похожесть - номер важнее
            street_weight = 0.2
            number_weight = 0.8
        
        # Но для каждой строки индивидуально: если улица очень похожа, увеличиваем её вес
        # Вычисляем веса для каждой строки отдельно
        final_scores: list[float] = []
        for _, row in df_filtered.iterrows():
            street_sim = row["street_sim"]
            num_score = row["number_score"]
            
            # Индивидуальная корректировка весов на основе похожести улицы
            if street_sim >= 0.95:
                # Почти точное совпадение улицы (>= 95%) - улица критически важна
                # Даже если номер не совпадает, это может быть правильная улица
                s_weight = 0.6
                n_weight = 0.4
            elif street_sim >= 0.9:
                # Очень похожая улица (>= 90%) - улица важна
                s_weight = 0.5
                n_weight = 0.5
            elif street_sim >= 0.85:
                # Похожая улица (>= 85%) - баланс в пользу улицы
                s_weight = 0.4
                n_weight = 0.6
            elif street_sim >= 0.75:
                # Средняя похожесть - стандартные веса
                s_weight = 0.3
                n_weight = 0.7
            else:
                # Низкая похожесть - номер важнее
                s_weight = 0.2
                n_weight = 0.8
            
            score = s_weight * street_sim + n_weight * num_score
            
            # Дополнительные бонусы
            c_number_parsed = parse_house_number_full(row["number_norm"])
            
            # Бонус 1: Если улица точно совпадает (>= 0.95) и base номера совпадает,
            # но есть дополнительные компоненты (строение, корпус) - это всё ещё хороший результат
            if (street_sim >= 0.95 and 
                q_number_parsed.base is not None and 
                c_number_parsed.base is not None and
                q_number_parsed.base == c_number_parsed.base and
                num_score < 1.0):
                # Base совпадает, но есть дополнительные компоненты - даём большой бонус
                # Если улица точно совпадает (1.0), даём минимум 0.95
                # Это выше, чем другие улицы с точным номером, но не точной улицей
                if street_sim >= 0.99:
                    score = max(score, 0.95)  # Почти максимальный score
                else:
                    score = max(score, street_sim * 0.9)  # 90% от похожести улицы
            
            # Бонус 2: Если улица точно совпадает (>= 0.99), но номер не совпадает вообще
            elif street_sim >= 0.99 and num_score < 0.1:
                # Улица точно правильная (>= 99%), но номера нет
                # Даём очень высокий score - правильная улица важнее неточного номера
                score = max(score, 0.92)  # Очень высокий score для точной улицы
            # Бонус 3: Если улица очень похожа (>= 0.95), но номер не совпадает вообще
            elif street_sim >= 0.95 and num_score < 0.1:
                # Улица почти точно правильная (>= 95%), но номера нет
                # Даём высокий минимальный score, чтобы показать правильную улицу
                score = max(score, street_sim * 0.8)  # Минимум 76% от похожести улицы
            elif street_sim >= 0.9 and num_score < 0.1:
                # Улица очень похожа (>= 90%), но номера нет
                score = max(score, street_sim * 0.7)  # Минимум 63% от похожести улицы
            
            final_scores.append(score)
        
        df_filtered["final_score"] = final_scores
    else:
        # Когда номера нет, больше опираемся на улицу
        street_weight = SCORE_STREET_WEIGHT
        number_weight = SCORE_NUMBER_WEIGHT
        
        df_filtered["final_score"] = (
            street_weight * df_filtered["street_sim"]
            + number_weight * df_filtered["number_score"]
        )
    
    # Дополнительный бонус за полное совпадение (и улица, и номер)
    if has_number_in_query:
        exact_match_mask = (
            (df_filtered["street_sim"] >= 0.95)
            & (df_filtered["number_score"] == 1.0)
        )
        df_filtered.loc[exact_match_mask, "final_score"] = 1.0
        
        # Также даём небольшой бонус, если улица очень похожа (>= 0.85), даже если номер не точный
        # Но это уже учитывается в индивидуальных весах выше, поэтому не дублируем
        pass
    
    # 9. Сортировка и выбор топ-N
    df_sorted = df_filtered.nlargest(limit, "final_score")
    
    # 10. Формирование ответа
    parsed_query_debug: Dict[str, Any] | None = None
    if debug:
        street_parts = _decompose_street(q_street_norm)
        parsed_query_debug = {
            "raw_city": city_raw,
            "raw_street": street_raw,
            "raw_number": number_raw,
            "city_norm": q_city_norm,
            "street_norm": street_parts["street_norm"],
            "street_core": street_parts["street_core"],
            "street_adj": street_parts["street_adj"],
            "street_type": street_parts["street_type"],
            "number_norm": q_number_norm,
            "number_parsed": {
                "base": q_number_parsed.base,
                "corp": q_number_parsed.corpus,
                "stroenie": q_number_parsed.building,
                "litera": q_number_parsed.letter,
            },
        }

    objects = []
    for _, row in df_sorted.iterrows():
        # Собираем нормализованный адрес в формате организаторов
        city_val = str(row["city"]) if row.get("city") else ""
        street_val = str(row["street"]) if row.get("street") else ""
        number_val = str(row["housenumber"]) if row.get("housenumber") else ""
        
        # Нормализуем для формирования полного адреса
        city_norm_val = norm_city(city_val) if city_val else "москва"
        street_norm_val = norm_street(street_val) if street_val else ''
        number_norm_val = norm_number(number_val) if number_val else ''
        
        # Формируем нормализованный адрес в требуемом формате
        normalized_address = build_full_norm(
            city_norm_val, 
            street_norm_val, 
            number_norm_val, 
            for_display=True
        ) if street_norm_val else ''
        
        obj: Dict[str, Any] = {
            "locality": city_val,
            "street": street_val,
            "number": number_val,
            "normalized_address": normalized_address,  # Нормализованный адрес в формате организаторов
            "lon": float(row["lon"]),
            "lat": float(row["lat"]),
            "score": round(float(row["final_score"]), 4),
        }

        if debug:
            obj["score_decomposition"] = {
                "street_sim": float(row["street_sim"]),
                "number_score": float(row["number_score"]),
                "final_score": round(float(row["final_score"]), 4),
            }
            obj["debug"] = {
                "street_norm": row["street_norm"],
                "number_norm": row["number_norm"],
                "base_num": parse_house_number_full(row["number_norm"]).base,
                "distance_on_number_axis": float(row["number_distance"]),
            }

        objects.append(obj)
    
    result: Dict[str, Any] = {
        "searched_address": query,
        "objects": objects,
    }
    if debug and parsed_query_debug is not None:
        result["parsed_query"] = parsed_query_debug
    return result


def geocode_improved(query: str, limit: int = 5, debug: bool = False) -> Dict[str, Any]:
    """
    Улучшенный геокодер с фуззи-поиском и умным скорингом.
    
    Стратегия (Вариант 4):
    1. Сначала пробуем строгий поиск (baseline)
    2. Если baseline нашёл результаты - возвращаем их
    3. Если baseline ничего не нашёл - включаем фуззи-алгоритм
    
    Это гарантирует, что там, где baseline уже работает хорошо,
    мы не портим результат фуззи-поиском.
    
    Args:
        query: Строка запроса
        limit: Максимальное количество результатов
        
    Returns:
        Словарь с результатами геокодирования
    """
    # В debug-режиме всегда используем фуззи-алгоритм, чтобы вернуть детальное объяснение.
    if debug:
        return geocode_improved_fuzzy_only(query, limit=limit, debug=True)

    # Импортируем здесь, чтобы избежать циклических зависимостей
    from .geocode_basic import geocode_basic
    
    # 1. Пробуем строгий (baseline) поиск
    res_basic = geocode_basic(query, limit=limit)
    
    # 2. Если baseline нашёл результаты, возвращаем их
    # Это сохраняет точность на "чистых" адресах
    if res_basic["objects"]:
        # Можно немного улучшить score, но координаты и результаты те же
        return res_basic
    
    # 3. Если baseline ничего не нашёл - включаем фуззи-алгоритм
    # Это помогает с опечатками, неточными запросами и т.п.
    return geocode_improved_fuzzy_only(query, limit=limit, debug=False)

