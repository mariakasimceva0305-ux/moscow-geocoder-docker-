"""
Модуль нормализации адресных компонентов.
"""

import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# Словарь нормализации типов улиц (ФИАС-подобный)
STREET_TYPE_MAP = {
    # улица
    'ул': 'улица',
    'ул.': 'улица',
    'улица': 'улица',
    'у': 'улица',
    # проспект
    'пр-т': 'проспект',
    'просп.': 'проспект',
    'просп': 'проспект',
    'проспект': 'проспект',
    'пр': 'проспект',  # может быть проезд, но приоритет проспекту
    # проезд
    'пр-д': 'проезд',
    'проезд': 'проезд',
    # переулок
    'пер': 'переулок',
    'пер.': 'переулок',
    'переулок': 'переулок',
    # бульвар
    'бул': 'бульвар',
    'бул.': 'бульвар',
    'бульвар': 'бульвар',
    # шоссе
    'ш': 'шоссе',
    'ш.': 'шоссе',
    'шос.': 'шоссе',
    'шоссе': 'шоссе',
    # набережная
    'наб': 'набережная',
    'наб.': 'набережная',
    'набережная': 'набережная',
    # площадь
    'пл': 'площадь',
    'пл.': 'площадь',
    'площадь': 'площадь',
    # аллея
    'ал': 'аллея',
    'ал.': 'аллея',
    'аллея': 'аллея',
    # тупик
    'туп': 'тупик',
    'туп.': 'тупик',
    'тупик': 'тупик',
}

# Словарь нормализации прилагательных
ADJECTIVE_MAP = {
    'б': 'большая',
    'б.': 'большая',
    'бол': 'большая',
    'больш': 'большая',
    'большая': 'большая',
    'большой': 'большая',
    'большое': 'большая',
    'м': 'малая',
    'м.': 'малая',
    'мал': 'малая',
    'малая': 'малая',
    'малый': 'малая',
    'малое': 'малая',
    'нов': 'новая',
    'нов.': 'новая',
    'новая': 'новая',
    'новый': 'новая',
    'новое': 'новая',
    'стар': 'старая',
    'ст.': 'старая',
    'старая': 'старая',
    'старый': 'старая',
    'старое': 'старая',
}


def norm_city(s: str) -> str:
    """
    Нормализует название города.
    
    - Всё в нижний регистр
    - Убирает г., город, точки и лишние пробелы
    - "Moscow" → "москва"
    - Если содержит "москва" → возвращает "москва"
    
    Args:
        s: Исходная строка
        
    Returns:
        Нормализованное название города
    """
    if not s:
        return ''
    
    s = s.strip().lower()
    
    # Убираем точки, запятые
    s = re.sub(r'[.,;]', '', s)
    
    # Убираем префиксы
    s = re.sub(r'^г\.?\s*', '', s)
    s = re.sub(r'^город\s+', '', s)
    
    # Убираем лишние пробелы
    s = re.sub(r'\s+', ' ', s).strip()
    
    # Английское название
    if 'moscow' in s:
        return 'москва'
    
    # Если содержит "москва" - возвращаем просто "москва"
    if 'москва' in s:
        return 'москва'
    
    return s


def norm_street(s: str) -> str:
    """
    Нормализует название улицы.
    
    - Нижний регистр
    - Убирает точки и лишние пробелы
    - Нормализует тип улицы (ул → улица, пр-т → проспект, и т.д.)
    - Нормализует прилагательные (Б → большая, М → малая, и т.д.)
    - Формат: "большая серпуховская улица", "мира проспект"
    
    Args:
        s: Исходное название улицы
        
    Returns:
        Нормализованное название улицы
    """
    if not s:
        return ''
    
    s = s.strip().lower()
    
    # Убираем точки, запятые
    s = re.sub(r'[.,;]', '', s)
    
    # Убираем лишние пробелы
    s = re.sub(r'\s+', ' ', s).strip()
    
    # Разбиваем на токены
    tokens = s.split()
    
    if not tokens:
        return ''
    
    normalized_tokens = []
    street_type_found = None
    adjective_found = None
    
    # Ищем тип улицы и прилагательное
    for token in tokens:
        # Проверяем тип улицы
        token_clean = token.rstrip('.')
        if token_clean in STREET_TYPE_MAP:
            street_type_found = STREET_TYPE_MAP[token_clean]
            continue
        
        # Проверяем прилагательное
        if token in ADJECTIVE_MAP:
            adjective_found = ADJECTIVE_MAP[token]
            continue
        
        # Обычное слово
        normalized_tokens.append(token)
    
    # Собираем результат: прилагательное + название + тип
    # ВАЖНО: согласно требованиям организаторов, названия должны быть БЕЗ сокращений
    # ул. -> улица, пер. -> переулок, пр-т -> проспект и т.д.
    result_parts = []
    if adjective_found:
        result_parts.append(adjective_found)
    
    if normalized_tokens:
        result_parts.extend(normalized_tokens)
    
    if street_type_found:
        # street_type_found уже в полном виде (из STREET_TYPE_MAP)
        result_parts.append(street_type_found)
    elif adjective_found or normalized_tokens:
        # Если есть прилагательное или название, но нет типа улицы,
        # добавляем "улица" по умолчанию (самый частый тип)
        result_parts.append('улица')
    
    return ' '.join(result_parts) if result_parts else s


def norm_number(s: str) -> str:
    """
    Нормализует номер дома.
    
    Согласно требованиям организаторов, формат: {номер дома} {номер корпус} {строение}
    Пример: "50 к1 с15"
    
    Приводит к единому формату:
    - "12к1", "12 к1", "12корп.1" → "12 к1" (сокращённый формат для хранения)
    - "12с2", "12 с2", "12 стр 2" → "12 с2"
    - "12/1" → "12 к1" (дробь как корпус)
    - "12А" → "12а" (литера)
    
    Для итогового вывода используем сокращения к/с, для внутренней обработки можно полные слова.
    
    Args:
        s: Исходный номер дома
        
    Returns:
        Нормализованный номер дома (например, "12 к1 с2")
    """
    if not s:
        return ''
    
    s = s.strip()
    
    # Убираем точки
    s = re.sub(r'\.', '', s)
    
    # Нормализуем корпус: используем сокращение "к" для компактности
    s = re.sub(r'(\d+)\s*к\s*(\d+)', r'\1 к\2', s, flags=re.IGNORECASE)
    s = re.sub(r'(\d+)\s*корп\.?\s*(\d+)', r'\1 к\2', s, flags=re.IGNORECASE)
    s = re.sub(r'(\d+)\s*корпус\s*(\d+)', r'\1 к\2', s, flags=re.IGNORECASE)
    
    # Нормализуем строение: используем сокращение "с"
    s = re.sub(r'(\d+)\s*с\s*(\d+)', r'\1 с\2', s, flags=re.IGNORECASE)
    s = re.sub(r'(\d+)\s*стр\.?\s*(\d+)', r'\1 с\2', s, flags=re.IGNORECASE)
    s = re.sub(r'(\d+)\s*строение\s*(\d+)', r'\1 с\2', s, flags=re.IGNORECASE)
    
    # Дробь как корпус
    s = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1 к\2', s)
    
    # Приводим литеры к нижнему регистру
    s = re.sub(r'([А-ЯЁ])', lambda m: m.group(1).lower(), s)
    
    # Убираем лишние пробелы
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s


@dataclass
class HouseNumberParsed:
    """Разобранный номер дома."""
    base: Optional[int] = None       # основной номер, например 12
    corpus: Optional[int] = None     # корпус, если есть
    building: Optional[int] = None   # строение, если есть
    letter: Optional[str] = None     # литера, если есть


def parse_house_number_full(norm_number: str) -> HouseNumberParsed:
    """
    Разбирает нормализованный номер дома на компоненты.
    
    Поддерживает форматы: "12 к1", "12 с2", "12 к1 с2"
    
    Args:
        norm_number: Нормализованный номер (например, "12 к1" или "12 с2")
        
    Returns:
        HouseNumberParsed с разобранными компонентами
    """
    if not norm_number:
        return HouseNumberParsed()
    
    result = HouseNumberParsed()
    
    # Извлекаем основной номер (первое число)
    base_match = re.search(r'^(\d+)', norm_number)
    if base_match:
        result.base = int(base_match.group(1))
    
    # Извлекаем корпус (формат: "к1", "к 1", "корпус 1")
    corpus_match = re.search(r'к\s*(\d+)', norm_number, flags=re.IGNORECASE)
    if corpus_match:
        result.corpus = int(corpus_match.group(1))
    else:
        # Пробуем полную форму
        corpus_match = re.search(r'корпус\s+(\d+)', norm_number)
        if corpus_match:
            result.corpus = int(corpus_match.group(1))
    
    # Извлекаем строение (формат: "с1", "с 1", "строение 1")
    building_match = re.search(r'с\s*(\d+)', norm_number, flags=re.IGNORECASE)
    if building_match:
        result.building = int(building_match.group(1))
    else:
        # Пробуем полную форму
        building_match = re.search(r'строение\s+(\d+)', norm_number)
        if building_match:
            result.building = int(building_match.group(1))
    
    # Извлекаем литеру (кириллица или латиница после номера)
    letter_match = re.search(r'(\d+)\s*([а-яёa-z]+)', norm_number)
    if letter_match:
        letter = letter_match.group(2)
        # Проверяем, что это не слово "корпус", "строение", "к", "с"
        if letter not in ['корпус', 'строение', 'к', 'с'] and len(letter) == 1:
            result.letter = letter
    
    return result


def format_number_for_display(norm_number: str) -> str:
    """
    Форматирует нормализованный номер дома для вывода.
    Заменяет сокращения на полные слова: к -> корпус, с -> строение
    
    Примеры:
    - "12 к1" -> "12 корпус 1"
    - "12 с1" -> "12 строение 1"
    - "50 к1 с15" -> "50 корпус 1 строение 15"
    
    Args:
        norm_number: Нормализованный номер (например, "12 к1")
        
    Returns:
        Отформатированный номер для вывода (например, "12 корпус 1")
    """
    if not norm_number:
        return ''
    
    # Заменяем сокращения на полные слова
    result = norm_number
    
    # Заменяем "к" на "корпус" (только если это не часть другого слова)
    result = re.sub(r'(\d+)\s*к\s*(\d+)', r'\1 корпус \2', result, flags=re.IGNORECASE)
    
    # Заменяем "с" на "строение" (только если это не часть другого слова)
    result = re.sub(r'(\d+)\s*с\s*(\d+)', r'\1 строение \2', result, flags=re.IGNORECASE)
    
    # Убираем лишние пробелы
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def build_full_norm(city: str, street: str, number: str, for_display: bool = False) -> str:
    """
    Строит полный нормализованный адрес.
    
    Внутренний формат (for_display=False, для сравнения):
    - В нижнем регистре, разделитель пробел
    - Пример: "москва тверская улица 12 к1"
    
    Формат для вывода (for_display=True, согласно требованиям организаторов):
    - Формат: {город}, {улица}, {номер дома} {номер корпус} {строение}
    - Пример: "Москва, Дорожная улица, 50 корпус 1 строение 15"
    - Пример: "Москва, Стремянный переулок, 14 строение 1"
    - Город и название улицы с заглавной буквы, тип улицы (улица, переулок и т.д.) - с маленькой буквы
    - Разделитель - запятые
    - Полные слова: "корпус" и "строение" вместо сокращений "к" и "с"
    
    Args:
        city: Нормализованный город (например, "москва")
        street: Нормализованная улица (например, "тверская улица")
        number: Нормализованный номер (например, "12 к1")
        for_display: Если True, возвращает форматированный адрес для вывода
        
    Returns:
        Полный нормализованный адрес
    """
    parts = []
    
    if city:
        if for_display:
            city_formatted = city.capitalize()
        else:
            city_formatted = city
        parts.append(city_formatted)
    
    if street:
        if for_display:
            street_words = street.split()
            # Список типов улиц, которые должны быть с маленькой буквы
            street_types_lower = {'улица', 'проспект', 'проезд', 'переулок', 'бульвар', 
                                  'шоссе', 'набережная', 'площадь', 'аллея', 'тупик'}
            # Форматируем: типы улиц - с маленькой буквы, остальные слова - с заглавной
            formatted_words = []
            for word in street_words:
                if word.lower() in street_types_lower:
                    formatted_words.append(word.lower())
                else:
                    formatted_words.append(word.capitalize())
            street_formatted = ' '.join(formatted_words)
        else:
            street_formatted = street
        parts.append(street_formatted)
    
    if number:
        if for_display:
            # Для вывода заменяем сокращения на полные слова
            number_formatted = format_number_for_display(number)
        else:
            number_formatted = number
        parts.append(number_formatted)
    
    if for_display:
        # Формат для вывода: "Москва, Дорожная улица, 50 корпус 1 строение 15"
        if len(parts) >= 2:
            result = f"{parts[0]}, {parts[1]}"
            if len(parts) > 2:
                result += f", {parts[2]}"
            return result
        elif len(parts) == 1:
            return parts[0]
        else:
            return ""
    else:
        # Внутренний формат для сравнения: "москва тверская улица 12 к1"
        return ' '.join(parts) if parts else ""


def add_normalized_columns(df) -> pd.DataFrame:
    """
    Добавляет нормализованные колонки к DataFrame.
    
    Args:
        df: DataFrame с колонками city, street, housenumber
        
    Returns:
        DataFrame с добавленными колонками:
        - city_norm, street_norm, number_norm, full_norm
    """
    df = df.copy()
    
    df['city_norm'] = df['city'].apply(norm_city)
    df['street_norm'] = df['street'].apply(norm_street)
    df['number_norm'] = df['housenumber'].apply(norm_number)
    
    # Если city_norm пустой, но данные из Москвы (координаты в пределах Москвы),
    # устанавливаем "москва" по умолчанию
    # Москва примерно: lat 55.5-55.9, lon 37.3-37.9
    moscow_mask = (
        (df['city_norm'] == '') & 
        (df['lat'] >= 55.5) & (df['lat'] <= 55.9) &
        (df['lon'] >= 37.3) & (df['lon'] <= 37.9)
    )
    df.loc[moscow_mask, 'city_norm'] = 'москва'
    
    df['full_norm'] = df.apply(
        lambda row: build_full_norm(
            row['city_norm'],
            row['street_norm'],
            row['number_norm']
        ),
        axis=1
    )
    
    return df

