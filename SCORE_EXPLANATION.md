# Как считается score (скор) в улучшенном геокодере

## Общая формула

Финальный score вычисляется как **взвешенная сумма** двух компонентов:

```
final_score = street_weight × street_sim + number_weight × number_score
```

Где:
- `street_sim` — похожесть улицы (0.0 - 1.0)
- `number_score` — похожесть номера дома (0.0 - 1.0)
- `street_weight` и `number_weight` — веса компонентов

## Веса компонентов

Веса зависят от того, указан ли номер дома в запросе:

### Если номер дома указан в запросе:
- `street_weight = 0.2` (20%)
- `number_weight = 0.8` (80%)

Номер дома становится критически важным.

### Если номер дома НЕ указан:
- `street_weight = 0.25` (25%)
- `number_weight = 0.75` (75%)

## 1. Похожесть улицы (street_sim)

### Шаг 1: Фуззи-поиск по нормализованным названиям улиц

Используется библиотека RapidFuzz с метрикой `QRatio`:

```python
from rapidfuzz import fuzz, process

street_matches = process.extract(
    query_street_norm,      # Нормализованное название улицы из запроса
    unique_streets,         # Все уникальные нормализованные улицы в базе
    scorer=fuzz.QRatio,     # Метрика похожести
    limit=15                # Топ-15 кандидатов
)
```

### Шаг 2: Фильтрация по минимальному score

Только улицы с score >= 0.6 (60%) попадают в кандидаты:

```python
matching_streets = [
    street for street, score, _ in street_matches
    if score >= 0.6 * 100  # RapidFuzz возвращает 0-100
]
```

### Шаг 3: Нормализация к 0-1

```python
street_sim = score / 100.0
```

**Пример:**
- Запрос: "стремянный переулок"
- Найдено: "стремянный переулок" → score = 100 → street_sim = 1.0
- Найдено: "старомонетный переулок" → score = 82.9 → street_sim = 0.829

## 2. Похожесть номера дома (number_score)

### Шаг 1: Парсинг номера дома

Номер дома разбирается на компоненты:

```python
@dataclass
class HouseNumberParsed:
    base: int | None       # Основной номер (14)
    corpus: int | None     # Корпус (1)
    building: int | None   # Строение (1)
    letter: str | None     # Литера ("а")
```

**Примеры:**
- "14 с1" → base=14, building=1
- "12к1" → base=12, corpus=1
- "25/19" → base=25, corpus=19
- "14" → base=14

### Шаг 2: Вычисление числовой дистанции

Функция `house_number_distance()` вычисляет "дистанцию" между запросом и кандидатом:

#### Основной номер (base):
```python
if base_diff == 0:
    distance += 0           # Полное совпадение
elif base_diff == 1:
    distance += 5           # Соседние дома (14 vs 15)
else:
    distance += 10 + 5 * base_diff  # Для больших различий
```

#### Корпус (corpus):
```python
if оба есть:
    distance += 5 * abs(corpus_q - corpus_c)
elif запрос имеет корпус, а кандидат нет:
    distance += 30          # Большой штраф
elif кандидат имеет корпус, а запрос нет:
    distance += 5           # Малый штраф
```

#### Строение (building):
```python
if оба есть:
    distance += 3 * abs(building_q - building_c)
elif запрос имеет строение, а кандидат нет:
    distance += 20
elif кандидат имеет строение, а запрос нет:
    distance += 3
```

#### Литера (letter):
```python
if оба есть и разные:
    distance += 2
elif запрос имеет литеру, а кандидат нет:
    distance += 10
elif кандидат имеет литеру, а запрос нет:
    distance += 1
```

### Шаг 3: Преобразование дистанции в score

Используется экспоненциальное убывание:

```python
if distance == 0:
    number_score = 1.0      # Полное совпадение
else:
    number_score = exp(-distance / BETA)
```

Где `BETA = 3.0` (параметр из конфигурации).

**Примеры вычислений:**

| Запрос | Кандидат | Distance | number_score = exp(-distance/3.0) |
|--------|----------|----------|----------------------------------|
| 14 с1  | 14 с1    | 0        | 1.000                            |
| 14 с1  | 14 с2    | 3        | 0.368                            |
| 14 с1  | 15 с1    | 5        | 0.189                            |
| 14 с1  | 14 к1    | 20       | 0.001                            |
| 14 с1  | 2        | 12       | 0.018                            |

## 3. Финальный score

### Базовая формула:

```python
final_score = street_weight × street_sim + number_weight × number_score
```

### Бонус за точное совпадение:

Если номер дома указан в запросе и есть **полное совпадение** (и улица, и номер):

```python
if street_sim >= 0.95 and number_score == 1.0:
    final_score = 1.0  # Максимальный score
```

## Примеры вычисления

### Пример 1: Точное совпадение

**Запрос:** "стремянный переулок 14 с1"

1. **street_sim:**
   - Улица: "стремянный переулок" → найдено точно → street_sim = 1.0

2. **number_score:**
   - Номер: "14 с1" (base=14, building=1)
   - Кандидат: "14 с1" (base=14, building=1)
   - distance = 0 → number_score = 1.0

3. **final_score:**
   - street_weight = 0.2, number_weight = 0.8
   - final_score = 0.2 × 1.0 + 0.8 × 1.0 = **1.0** ✅
   - Бонус: street_sim >= 0.95 и number_score == 1.0 → **final_score = 1.0**

### Пример 2: Частичное совпадение

**Запрос:** "стремянный переулок 14 с1"  
**Кандидат:** "стремянный переулок 14 с2"

1. **street_sim:**
   - Улица совпадает → street_sim = 1.0

2. **number_score:**
   - Запрос: base=14, building=1
   - Кандидат: base=14, building=2
   - distance = 3 × |1 - 2| = 3
   - number_score = exp(-3/3.0) = exp(-1) ≈ **0.368**

3. **final_score:**
   - final_score = 0.2 × 1.0 + 0.8 × 0.368 = 0.2 + 0.294 = **0.494**

### Пример 3: Похожая улица, точный номер

**Запрос:** "старомонетный переулок 14 с1"  
**Кандидат:** "стремянный переулок 14 с1"

1. **street_sim:**
   - "старомонетный" vs "стремянный" → score ≈ 82.9 → street_sim = **0.829**

2. **number_score:**
   - Номер точно совпадает → number_score = **1.0**

3. **final_score:**
   - final_score = 0.2 × 0.829 + 0.8 × 1.0 = 0.166 + 0.8 = **0.966**

## Параметры конфигурации

Все параметры настраиваются в `src/config.py`:

```python
FUZZY_MATCH_MIN_SCORE = 0.6           # Минимальный score для улицы
FUZZY_TOP_K = 15                      # Топ-K кандидатов для фуззи-поиска
HOUSE_NUMBER_DISTANCE_BETA = 3.0      # Параметр экспоненциального убывания
SCORE_STREET_WEIGHT = 0.25            # Вес улицы (если номер не указан)
SCORE_NUMBER_WEIGHT = 0.75            # Вес номера (если номер не указан)
```

## Итоговая формула (компактно)

```
1. street_sim = fuzz_ratio(query_street, candidate_street) / 100
   (только если >= 0.6)

2. distance = house_number_distance(query_number, candidate_number)
   (с учётом base, corpus, building, letter)

3. number_score = exp(-distance / 3.0) if distance > 0 else 1.0

4. weights = (0.2, 0.8) if has_number_in_query else (0.25, 0.75)

5. final_score = weights[0] × street_sim + weights[1] × number_score

6. if street_sim >= 0.95 and number_score == 1.0:
       final_score = 1.0  # Бонус за точное совпадение
```



