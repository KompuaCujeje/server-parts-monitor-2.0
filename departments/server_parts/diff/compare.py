# departments/server_parts/diff/compare.py
#
# Сравнивает два снимка (вчера/сегодня) и строит дайджест изменений цен.
# Диски матчатся строго по part_number (см. catalog.yaml, match_type: serial).
# Память матчится по совпадению всех match_keywords в тексте карточки
# (match_type: text) — это и есть "текстовый матчинг по названию".

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from typing import Optional
import yaml


@dataclass
class PriceChange:
    product_id: str
    display_name: str
    source_id: str
    category: str
    price_before: Optional[float]
    price_after: Optional[float]
    change_abs: Optional[float]
    change_pct: Optional[float]
    url: str


def load_catalog(path: str = "catalog.yaml") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["products"]


def load_snapshot(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_product(item: dict, catalog_entry: dict) -> bool:
    if catalog_entry["category"] != item.get("category"):
        return False

    if catalog_entry["match_type"] == "serial":
        return item.get("part_number") in catalog_entry.get("aliases", [])

    if catalog_entry["match_type"] == "text":
        text = (item.get("title", "") + " " + item.get("raw_text", "")).lower()
        return all(keyword.lower() in text for keyword in catalog_entry["match_keywords"])

    return False


def find_price(snapshot: list[dict], catalog_entry: dict, source_id: str) -> tuple[Optional[float], str]:
    for item in snapshot:
        if item.get("source_id") == source_id and match_product(item, catalog_entry):
            return item.get("price"), item.get("url", "")
    return None, ""


def build_digest(
    catalog_path: str,
    snapshot_before_path: str,
    snapshot_after_path: str,
    source_ids: list[str],
) -> list[PriceChange]:
    catalog = load_catalog(catalog_path)
    before = load_snapshot(snapshot_before_path)
    after = load_snapshot(snapshot_after_path)

    changes: list[PriceChange] = []
    for entry in catalog:
        for source_id in source_ids:
            price_before, _ = find_price(before, entry, source_id)
            price_after, url_after = find_price(after, entry, source_id)

            if price_before is None and price_after is None:
                continue  # товара нет ни в одном снимке у этого источника

            change_abs = None
            change_pct = None
            if price_before is not None and price_after is not None:
                change_abs = round(price_after - price_before, 2)
                change_pct = round((change_abs / price_before) * 100, 2) if price_before else None

            changes.append(PriceChange(
                product_id=entry["id"],
                display_name=entry["display_name"],
                source_id=source_id,
                category=entry["category"],
                price_before=price_before,
                price_after=price_after,
                change_abs=change_abs,
                change_pct=change_pct,
                url=url_after,
            ))
    return changes


def digest_to_markdown(changes: list[PriceChange]) -> str:
    lines = ["# Дайджест изменений цен\n"]
    moved = [c for c in changes if c.change_pct not in (None, 0)]
    if not moved:
        lines.append("Изменений цен не обнаружено.")
        return "\n".join(lines)

    for c in sorted(moved, key=lambda x: abs(x.change_pct or 0), reverse=True):
        arrow = "\u2b06" if c.change_pct > 0 else "\u2b07"
        lines.append(
            f"- {arrow} **{c.display_name}** ({c.source_id}): "
            f"{c.price_before:.0f} → {c.price_after:.0f} ₽ "
            f"({c.change_pct:+.2f}%)  [ссылка]({c.url})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    changes = build_digest(
        catalog_path="departments/server-parts/catalog.yaml",
        snapshot_before_path=sys.argv[1],
        snapshot_after_path=sys.argv[2],
        source_ids=["regard", "citilink", "onlinetrade", "kns", "hcom", "serverflow", "westcomp"],
    )
    print(digest_to_markdown(changes))
    with open("departments/server-parts/data/digest.json", "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in changes], f, ensure_ascii=False, indent=2)
