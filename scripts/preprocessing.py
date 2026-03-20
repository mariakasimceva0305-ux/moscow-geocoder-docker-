import osmium as osm
import csv
from shapely import wkt
from shapely.geometry import Point
from tqdm import tqdm


# Примерный bbox Москвы (можно подправить при желании)
MOSCOW_LAT_MIN = 55.2
MOSCOW_LAT_MAX = 56.1
MOSCOW_LON_MIN = 36.8
MOSCOW_LON_MAX = 38.1


class MoscowBoundaryHandler(osm.SimpleHandler):
    """
    Первый проход по PBF:
    пытаемся найти административную границу Москвы.
    boundary=administrative, name ~ Москва/Moscow.
    admin_level не жёстко фиксируем, а смотрим разные.
    """

    def __init__(self):
        super().__init__()
        self.wkt_factory = osm.geom.WKTFactory()
        self.candidates = []  # (admin_level, name, geometry)

    def area(self, a):
        tags = a.tags

        if tags.get("boundary") != "administrative":
            return

        name = tags.get("name", "") or ""
        name_lower = name.lower()
        if "москва" not in name_lower and "moscow" not in name_lower:
            return

        admin_level = tags.get("admin_level", "")

        try:
            mp_wkt = self.wkt_factory.create_multipolygon(a)
        except Exception:
            return

        try:
            geom = wkt.loads(mp_wkt)
        except Exception:
            return

        self.candidates.append((admin_level, name, geom))


def choose_moscow_boundary(candidates):
    """
    Из списка кандидатов с границами Москвы выбираем одну:
    - сначала по admin_level (предпочитаем 8, потом 6, 4),
    - если несколько — берём с максимальной площадью.
    """
    if not candidates:
        return None

    # приоритизируем admin_level
    preferred_levels = ["8", "6", "4", ""]

    for level in preferred_levels:
        level_candidates = [c for c in candidates if c[0] == level]
        if not level_candidates:
            continue

        # среди них берём с max площади
        best = max(level_candidates, key=lambda c: c[2].area)
        return best  # (admin_level, name, geom)

    # если вообще нет admin_level, берём просто самый большой по площади
    return max(candidates, key=lambda c: c[2].area)


class MoscowBuildingsHandler(osm.SimpleHandler):
    """
    Второй проход по PBF:
    собираем все building=*,
    считаем центроид и отбираем:
      - либо по попаданию в polygon Москвы (boundary),
      - либо по bbox, если границу не нашли.
    """

    def __init__(self, csv_writer, moscow_boundary_geom=None):
        super().__init__()
        self.writer = csv_writer
        self.boundary = moscow_boundary_geom  # shapely geometry или None
        self.wkt_factory = osm.geom.WKTFactory()
        self.pbar = tqdm(unit="obj", desc="Обрабатываем объекты OSM")

    def _in_moscow(self, lon, lat) -> bool:
        point = Point(lon, lat)
        if self.boundary is not None:
            return point.within(self.boundary)
        # fallback: просто bbox
        return (
            MOSCOW_LAT_MIN <= lat <= MOSCOW_LAT_MAX and
            MOSCOW_LON_MIN <= lon <= MOSCOW_LON_MAX
        )

    def _write_row(self, obj_id, tags, lon, lat):
        city = tags.get("addr:city", "") or ""
        street = tags.get("addr:street", "") or ""
        housenumber = tags.get("addr:housenumber", "") or ""

        self.writer.writerow({
            "osm_id": obj_id,
            "city": city,
            "street": street,
            "housenumber": housenumber,
            "lon": lon,
            "lat": lat,
        })

    # --- здания-ways (простые полигоны) ---
    def way(self, w):
        self.pbar.update(1)

        if "building" not in w.tags:
            return
        if not w.nodes:
            return

        lon_sum = 0.0
        lat_sum = 0.0
        count = 0

        for n in w.nodes:
            try:
                loc = n.location
                if not loc.valid():
                    continue
                lon_sum += loc.lon
                lat_sum += loc.lat
                count += 1
            except RuntimeError:
                continue

        if count == 0:
            return

        lon_center = lon_sum / count
        lat_center = lat_sum / count

        if not self._in_moscow(lon_center, lat_center):
            return

        self._write_row(w.id, w.tags, lon_center, lat_center)

    # --- здания-areas (мультиполигоны) ---
    def area(self, a):
        self.pbar.update(1)

        if "building" not in a.tags:
            return

        try:
            mp_wkt = self.wkt_factory.create_multipolygon(a)
        except Exception:
            return

        try:
            geom = wkt.loads(mp_wkt)
        except Exception:
            return

        centroid = geom.centroid

        if not self._in_moscow(centroid.x, centroid.y):
            return

        self._write_row(a.id, a.tags, centroid.x, centroid.y)


def find_moscow_boundary(pbf_path: str):
    """
    Первый проход:
    ищем границы Москвы и выбираем наиболее подходящую.
    Если ничего не нашли — возвращаем None.
    """
    handler = MoscowBoundaryHandler()
    print("Ищем границу Москвы в PBF...")
    handler.apply_file(pbf_path, locations=True)

    if not handler.candidates:
        print("⚠ Не удалось найти границу Москвы как area. Будем использовать bbox.")
        return None

    best = choose_moscow_boundary(handler.candidates)
    admin_level, name, geom = best
    print(f"Найдена граница Москвы: name='{name}', admin_level={admin_level}")
    return geom


def extract_moscow_buildings(pbf_path: str, csv_path: str):
    """
    Итоговый пайплайн:
      1) пробуем найти границу Москвы;
      2) вторым проходом собираем здания внутри границы или bbox.
    """
    moscow_boundary = find_moscow_boundary(pbf_path)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["osm_id", "city", "street", "housenumber", "lon", "lat"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        print(f"Парсим здания в {pbf_path}...")
        handler = MoscowBuildingsHandler(writer, moscow_boundary)
        handler.apply_file(pbf_path, locations=True)
        handler.pbar.close()

    print(f"Готово! Здания Москвы (по границе или bbox) сохранены в {csv_path}")


if __name__ == "__main__":
    from pathlib import Path
    
    # Определяем пути относительно расположения скрипта
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Путь к исходному PBF файлу в папке data
    PBF_FILE = project_root / "data" / "data.osm.pbf"
    
    # Выходной CSV файл в корне проекта
    OUT_CSV = project_root / "moscow_buildings.csv"
    
    # Проверяем, существует ли входной файл
    if not PBF_FILE.exists():
        print(f"Ошибка: файл {PBF_FILE} не найден!")
        print(f"Убедитесь, что файл data.osm.pbf находится в папке {project_root / 'data'}")
        exit(1)
    
    # Создаём папку data, если её нет
    PBF_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Входной файл: {PBF_FILE}")
    print(f"Выходной файл: {OUT_CSV}")
    print()
    
    extract_moscow_buildings(str(PBF_FILE), str(OUT_CSV))
