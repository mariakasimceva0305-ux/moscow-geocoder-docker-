"""
REST API для геокодирования адресов Москвы.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles

from .geocode_basic import geocode_basic, _get_cached_data
from .geocode_improved import geocode_improved

app = FastAPI(
    title="Геокодер адресов Москвы",
    description="API для геокодирования адресов по данным OpenStreetMap",
    version="0.1.0"
)

# Путь к статическим файлам
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup_event():
    """
    Предзагрузка данных при старте API.
    Это ускоряет первый запрос, так как данные уже будут загружены и нормализованы.
    
    Приоритет загрузки:
    1. Из БД (если USE_DATABASE=True и БД доступна) - быстрее
    2. Из CSV - fallback
    """
    print("Предзагрузка данных...")
    try:
        # Предзагружаем данные для базового геокодера
        # Функция сама определит источник (БД или CSV)
        _get_cached_data()
        print("✓ Данные успешно загружены")
    except Exception as e:
        print(f"⚠ Ошибка при предзагрузке данных: {e}")
        print("Данные будут загружены при первом запросе")


@app.get("/")
async def root():
    """Корневой эндпоинт - возвращает HTML интерфейс."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    else:
        return {
            "message": "Геокодер адресов Москвы API",
            "endpoints": {
                "/geocode/basic": "Базовый геокодер (точное сопоставление)",
                "/geocode/improved": "Улучшенный геокодер (фуззи-поиск)"
            }
        }


@app.get("/api")
async def api_info():
    """Информация об API."""
    return {
        "message": "Геокодер адресов Москвы API",
        "endpoints": {
            "/geocode/basic": "Базовый геокодер (точное сопоставление)",
            "/geocode/improved": "Улучшенный геокодер (фуззи-поиск)"
        }
    }


@app.get("/geocode/basic")
async def geocode_basic_endpoint(
    address: str = Query(..., description="Адрес для геокодирования"),
    limit: int = Query(5, ge=1, le=50, description="Максимальное количество результатов")
):
    """
    Базовый геокодер.
    
    Выполняет точное сопоставление по нормализованным полям.
    """
    try:
        result = geocode_basic(address, limit=limit)
        # Используем Response с json.dumps для поддержки ensure_ascii=False
        return Response(
            content=json.dumps(result, ensure_ascii=False),
            media_type="application/json"
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in geocode_basic: {e}")
        print(error_detail)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "error_type": type(e).__name__,
                "detail": error_detail if __debug__ else None
            }
        )


@app.get("/geocode/improved")
async def geocode_improved_endpoint(
    address: str = Query(..., description="Адрес для геокодирования"),
    limit: int = Query(5, ge=1, le=50, description="Максимальное количество результатов"),
    debug: bool = Query(False, description="Включить debug-режим (детальное объяснение работы алгоритма)"),
):
    """
    Улучшенный геокодер.
    
    Использует фуззи-поиск по улицам и умное сравнение номеров домов.
    """
    try:
        result = geocode_improved(address, limit=limit, debug=debug)
        # Используем Response с json.dumps для поддержки ensure_ascii=False
        return Response(
            content=json.dumps(result, ensure_ascii=False),
            media_type="application/json"
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in geocode_improved: {e}")
        print(error_detail)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "error_type": type(e).__name__,
                "detail": error_detail if __debug__ else None
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

