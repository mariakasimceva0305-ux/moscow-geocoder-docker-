"""
Тест соответствия требованиям организаторов по формату адресов.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.normalize import norm_city, norm_street, norm_number, build_full_norm
from src.geocode_basic import geocode_basic
from src.geocode_improved import geocode_improved

def test_1_normalized_address_format():
    """Тест 1: Формат нормализованного адреса"""
    print("="*70)
    print("ТЕСТ 1: Формат нормализованного адреса")
    print("="*70)
    
    test_cases = [
        {
            "city": "Москва",
            "street": "Дорожная улица",
            "number": "50 к1 с15",
            "expected": "Москва, Дорожная Улица, 50 к1 с15"
        },
        {
            "city": "Москва",
            "street": "Тверская улица",
            "number": "12 к1",
            "expected": "Москва, Тверская Улица, 12 к1"
        }
    ]
    
    all_passed = True
    for i, case in enumerate(test_cases, 1):
        city_norm = norm_city(case["city"])
        street_norm = norm_street(case["street"])
        number_norm = norm_number(case["number"])
        result = build_full_norm(city_norm, street_norm, number_norm, for_display=True)
        
        # Проверяем формат (город, улица, номер)
        parts = result.split(", ")
        if len(parts) >= 3:
            city_part = parts[0]
            street_part = parts[1]
            number_part = parts[2]
            
            print(f"\nТест 1.{i}:")
            print(f"  Вход: {case['city']}, {case['street']}, {case['number']}")
            print(f"  Выход: {result}")
            
            # Проверяем формат
            if len(parts) == 3 and city_part and street_part and number_part:
                print(f"  ✓ Формат корректен: {{город}}, {{улица}}, {{номер}}")
            else:
                print(f"  ✗ Формат некорректен!")
                all_passed = False
        else:
            print(f"  ✗ Неверное количество частей: {len(parts)}")
            all_passed = False
    
    return all_passed


def test_2_abbreviations():
    """Тест 2: Замена сокращений на полные названия"""
    print("\n" + "="*70)
    print("ТЕСТ 2: Замена сокращений на полные названия")
    print("="*70)
    
    test_cases = [
        ("Тверская ул.", "тверская улица", "ул. -> улица"),
        ("пер. Сретенский", "сретенский переулок", "пер. -> переулок"),
        ("Ленинский пр-т", "ленинский проспект", "пр-т -> проспект"),
        ("Большая Серпуховская ул.", "большая серпуховская улица", "ул. -> улица"),
    ]
    
    all_passed = True
    for i, (input_str, expected, description) in enumerate(test_cases, 1):
        result = norm_street(input_str)
        passed = result == expected
        status = "✓" if passed else "✗"
        
        print(f"\nТест 2.{i}: {description}")
        print(f"  Вход:  '{input_str}'")
        print(f"  Выход: '{result}'")
        print(f"  Ожидалось: '{expected}'")
        print(f"  {status} {'ПРОШЕЛ' if passed else 'НЕ ПРОШЕЛ'}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_3_house_number_format():
    """Тест 3: Формат номера дома"""
    print("\n" + "="*70)
    print("ТЕСТ 3: Формат номера дома")
    print("="*70)
    print("Формат: {{номер дома}} {{номер корпус}} {{строение}}")
    print("Пример: 50 к1 с15")
    
    test_cases = [
        ("50 к1 с15", "50 к1 с15", "Уже правильный формат"),
        ("50к1с15", "50 к1 с15", "Без пробелов"),
        ("50 корпус 1 строение 15", "50 к1 с15", "Полные слова"),
        ("12к1", "12 к1", "Только корпус"),
        ("12 с2", "12 с2", "Только строение"),
        ("12/1", "12 к1", "Дробь как корпус"),
    ]
    
    all_passed = True
    for i, (input_str, expected, description) in enumerate(test_cases, 1):
        result = norm_number(input_str)
        passed = result == expected
        status = "✓" if passed else "✗"
        
        print(f"\nТест 3.{i}: {description}")
        print(f"  Вход:  '{input_str}'")
        print(f"  Выход: '{result}'")
        print(f"  Ожидалось: '{expected}'")
        print(f"  {status} {'ПРОШЕЛ' if passed else 'НЕ ПРОШЕЛ'}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_4_word_order():
    """Тест 4: Порядок слов в названии улицы"""
    print("\n" + "="*70)
    print("ТЕСТ 4: Порядок слов в названии улицы")
    print("="*70)
    print("Порядок: прилагательное + название + тип")
    
    test_cases = [
        ("Большая Серпуховская ул.", "большая серпуховская улица", "Прилагательное + название + тип"),
        ("Тверская улица", "тверская улица", "Название + тип"),
        ("пер. Сретенский", "сретенский переулок", "Тип + название (переупорядочивается)"),
        ("Ленинский проспект", "ленинский проспект", "Название + тип"),
    ]
    
    all_passed = True
    for i, (input_str, expected, description) in enumerate(test_cases, 1):
        result = norm_street(input_str)
        
        # Проверяем, что сокращения заменены
        has_abbreviation = any(abb in result for abb in ["ул.", "пер.", "пр-т"])
        has_full_names = any(name in result for name in ["улица", "переулок", "проспект"])
        
        passed = result == expected and not has_abbreviation and has_full_names
        status = "✓" if passed else "✗"
        
        print(f"\nТест 4.{i}: {description}")
        print(f"  Вход:  '{input_str}'")
        print(f"  Выход: '{result}'")
        print(f"  Ожидалось: '{expected}'")
        print(f"  {status} {'ПРОШЕЛ' if passed else 'НЕ ПРОШЕЛ'}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_5_geocoder_integration():
    """Тест 5: Интеграция с геокодерами"""
    print("\n" + "="*70)
    print("ТЕСТ 5: Работа геокодеров с новым форматом")
    print("="*70)
    
    test_queries = [
        "Москва, Тверская ул., 12к1",
        "Москва, пер. Сретенский, 50",
        "Москва, Ленинский пр-т, 1",
    ]
    
    all_passed = True
    for i, query in enumerate(test_queries, 1):
        print(f"\nТест 5.{i}: Запрос '{query}'")
        
        try:
            # Базовый геокодер
            result_basic = geocode_basic(query, limit=3)
            print(f"  Базовый геокодер: найдено {len(result_basic['objects'])} результатов")
            if result_basic['objects']:
                obj = result_basic['objects'][0]
                print(f"    Пример: {obj['street']} {obj['number']}")
            
            # Улучшенный геокодер
            result_improved = geocode_improved(query, limit=3)
            print(f"  Улучшенный геокодер: найдено {len(result_improved['objects'])} результатов")
            if result_improved['objects']:
                obj = result_improved['objects'][0]
                print(f"    Пример: {obj['street']} {obj['number']} (score={obj['score']:.4f})")
            
            print(f"  ✓ Геокодеры работают")
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
            all_passed = False
    
    return all_passed


def main():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ СООТВЕТСТВИЯ ТРЕБОВАНИЯМ ОРГАНИЗАТОРОВ")
    print("="*70)
    print("\nПроверяемые требования:")
    print("1. Формат нормализованного адреса: {{город}}, {{улица}}, {{номер}} {{корпус}} {{строение}}")
    print("2. Сокращения заменяются: ул. -> улица, пер. -> переулок, пр-т -> проспект")
    print("3. Формат номера дома: {{номер}} {{корпус}} {{строение}} (например, 50 к1 с15)")
    print("4. Порядок слов в улице: прилагательное + название + тип")
    print("5. Интеграция с геокодерами")
    print()
    
    results = []
    
    # Тест 1
    results.append(("Формат нормализованного адреса", test_1_normalized_address_format()))
    
    # Тест 2
    results.append(("Замена сокращений", test_2_abbreviations()))
    
    # Тест 3
    results.append(("Формат номера дома", test_3_house_number_format()))
    
    # Тест 4
    results.append(("Порядок слов в названии улицы", test_4_word_order()))
    
    # Тест 5
    results.append(("Интеграция с геокодерами", test_5_geocoder_integration()))
    
    # Итоги
    print("\n" + "="*70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*70)
    
    for name, passed in results:
        status = "✓ ПРОШЕЛ" if passed else "✗ НЕ ПРОШЕЛ"
        print(f"{name:40} {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + "="*70)
    if all_passed:
        print("✓ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    else:
        print("✗ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
    print("="*70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


