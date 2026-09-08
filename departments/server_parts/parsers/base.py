# departments/server_parts/parsers/base.py
#
# Базовый класс для всех парсеров источников. Реализует двухуровневую логику:
# 1) страница категории -> список ссылок на карточки товара
# 2) карточка товара -> точная цена + (для дисков) серийный/парт-номер
#
# Каждый parser_module (regard.py, citilink.py, ...) наследуется от BaseParser
# и переопределяет только parse_listing_page() и parse_product_page().

from __future__ import annotations
import time
import re
from dataclasses import dataclass, field
from typing import Optional
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 1.5  # секунды, чтобы не долбить сайт слишком часто


@dataclass
class ProductSnapshot:
    source_id: str
    category: str          # "disk" или "ram"
    url: str
    title: str
    price: Optional[float]
    part_number: Optional[str] = None   # заполняется только для дисков
    raw_text: str = ""                  # полный текст карточки — для текстового матчинга памяти
    extra: dict = field(default_factory=dict)


class BaseParser:
    source_id: str = "base"

    def __init__(self, base_url: str, category_urls: dict[str, str]):
        self.base_url = base_url
        self.category_urls = category_urls
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, url: str) -> BeautifulSoup:
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        time.sleep(DELAY_BETWEEN_REQUESTS)
        return BeautifulSoup(resp.text, "html.parser")

    def run(self) -> list[ProductSnapshot]:
        """Главная точка входа: обходит все категории этого источника."""
        results: list[ProductSnapshot] = []
        for category, listing_url in self.category_urls.items():
            if not listing_url:
                continue  # источник ещё не настроен для этой категории
            product_links = self.parse_listing_page(listing_url, category)
            for link in product_links:
                snapshot = self.parse_product_page(link, category)
                if snapshot:
                    results.append(snapshot)
        return results

    # --- переопределяется в каждом конкретном парсере ---

    def parse_listing_page(self, url: str, category: str) -> list[str]:
        """Возвращает список URL карточек товара со страницы категории."""
        raise NotImplementedError

    def parse_product_page(self, url: str, category: str) -> Optional[ProductSnapshot]:
        """Открывает карточку товара, достаёт точную цену и (для дисков) парт-номер."""
        raise NotImplementedError

    # --- утилиты, общие для всех парсеров ---

    @staticmethod
    def extract_price(text: str) -> Optional[float]:
        """'35 500 ₽' -> 35500.0"""
        cleaned = re.sub(r"[^\d]", "", text)
        return float(cleaned) if cleaned else None

    @staticmethod
    def extract_part_number(text: str, known_part_numbers: list[str]) -> Optional[str]:
        """Ищет в тексте карточки один из известных парт-номеров из catalog.yaml."""
        upper_text = text.upper()
        for part_number in known_part_numbers:
            if part_number.upper() in upper_text:
                return part_number
        return None
