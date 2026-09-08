# departments/server_parts/run_all_parsers.py
#
# "Сборщик": читает sources.yaml и catalog.yaml, запускает парсер для каждого
# источника, у которого заполнены category_urls, сохраняет общий снимок
# в data/snapshot-today.json. Перед этим переносит вчерашний снимок
# в snapshot-yesterday.json, чтобы diff/compare.py было с чем сравнивать.

import json
import importlib
import shutil
from pathlib import Path
from dataclasses import asdict
import yaml

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def load_yaml(name: str) -> dict:
    with open(BASE_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def rotate_snapshots():
    today_path = DATA_DIR / "snapshot-today.json"
    yesterday_path = DATA_DIR / "snapshot-yesterday.json"
    if today_path.exists():
        shutil.copyfile(today_path, yesterday_path)


def run():
    sources_config = load_yaml("sources.yaml")["sources"]
    all_snapshots = []

    for source in sources_config:
        category_urls = {k: v for k, v in source["category_urls"].items() if v}
        if not category_urls:
            print(f"[skip] {source['id']}: category_urls не заполнены")
            continue

        module_path = f"departments.server_parts.{source['parser_module'].replace('parsers.', 'parsers.')}"
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            print(f"[skip] {source['id']}: модуль {module_path} ещё не написан")
            continue

        parser_class_name = source["id"].capitalize() + "Parser"
        parser_class = getattr(module, parser_class_name, None)
        if parser_class is None:
            print(f"[skip] {source['id']}: класс {parser_class_name} не найден в модуле")
            continue

        parser = parser_class(base_url=source["base_url"], category_urls=category_urls)
        try:
            snapshots = parser.run()
        except Exception as exc:
            print(f"[error] {source['id']}: {exc}")
            continue

        print(f"[ok] {source['id']}: собрано {len(snapshots)} товаров")
        all_snapshots.extend(asdict(s) for s in snapshots)

    rotate_snapshots()
    with open(DATA_DIR / "snapshot-today.json", "w", encoding="utf-8") as f:
        json.dump(all_snapshots, f, ensure_ascii=False, indent=2)

    print(f"Итого собрано товаров: {len(all_snapshots)}")


if __name__ == "__main__":
    run()
