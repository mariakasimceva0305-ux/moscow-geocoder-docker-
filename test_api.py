"""
Простой скрипт для тестирования API геокодера.
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_geocode(query: str, endpoint: str = "improved"):
    """Тестирует геокодер через API."""
    url = f"{API_URL}/geocode/{endpoint}"
    params = {"address": query}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None

if __name__ == "__main__":
    print("Тестирование геокодера API\n")
    
    # Тест 1: Базовый геокодер
    print("="*60)
    print("Тест 1: Базовый геокодер")
    print("="*60)
    result = test_geocode("Москва, Тверская улица, 12", "basic")
    if result:
        print(f"Запрос: {result['searched_address']}")
        print(f"Найдено результатов: {len(result['objects'])}")
        if result['objects']:
            obj = result['objects'][0]
            print(f"Первый результат: {obj['street']} {obj['number']}")
            print(f"Координаты: ({obj['lat']}, {obj['lon']})")
            print(f"Score: {obj['score']}")
    
    # Тест 2: Улучшенный геокодер
    print("\n" + "="*60)
    print("Тест 2: Улучшенный геокодер")
    print("="*60)
    result = test_geocode("Москва, Тверская улица, 12", "improved")
    if result:
        print(f"Запрос: {result['searched_address']}")
        print(f"Найдено результатов: {len(result['objects'])}")
        if result['objects']:
            for i, obj in enumerate(result['objects'][:3], 1):
                print(f"{i}. {obj['street']} {obj['number']}: score={obj['score']}")
    
    # Тест 3: Без номера дома
    print("\n" + "="*60)
    print("Тест 3: Поиск только улицы")
    print("="*60)
    result = test_geocode("большая серпуховская", "improved")
    if result:
        print(f"Запрос: {result['searched_address']}")
        print(f"Найдено результатов: {len(result['objects'])}")
        if result['objects']:
            for i, obj in enumerate(result['objects'][:3], 1):
                print(f"{i}. {obj['street']} {obj['number']}: score={obj['score']}")
    
    print("\n" + "="*60)
    print("Для интерактивной документации API откройте:")
    print("http://localhost:8000/docs")
    print("="*60)


