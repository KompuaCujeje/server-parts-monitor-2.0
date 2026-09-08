# departments/server_parts/parsers/regard.py
#
# ВАЖНО: селекторы (find/find_all с классами) — ориентировочные,
# основаны на типовой вёрстке каталога Regard. Перед первым реальным запуском
# нужно открыть страницу в браузере (F12 -> Inspect) и свериться с фактическими
# CSS-классами карточек, поскольку вёрстка сайта может обновляться.

from .base import BaseParser, ProductSnapshot

KNOWN_PART_NUMBERS = ["MZ7L33T8HBLT-00A07", "MZ7L33T8HBLT"]


class RegardParser(BaseParser):
    source_id = "regard"

    def parse_listing_page(self, url: str, category: str) -> list[str]:
        soup = self.fetch(url)
        links = []
        # Карточки товара в каталоге Regard обычно имеют ссылку вида /product/<id>/...
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/product/" in href:
                full_url = href if href.startswith("http") else self.base_url + href
                if full_url not in links:
                    links.append(full_url)
        return links

    def parse_product_page(self, url: str, category: str) -> ProductSnapshot | None:
        soup = self.fetch(url)

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Цена: ищем элемент, где обычно лежит текущая цена товара
        price_tag = soup.find(attrs={"itemprop": "price"}) or soup.find(class_=lambda c: c and "price" in c.lower())
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price = self.extract_price(price_text)

        full_text = soup.get_text(" ", strip=True)

        part_number = None
        if category == "disk":
            part_number = self.extract_part_number(full_text, KNOWN_PART_NUMBERS)

        if not title or price is None:
            return None  # карточка не распозналась — пропускаем, не пишем мусор в снимок

        return ProductSnapshot(
            source_id=self.source_id,
            category=category,
            url=url,
            title=title,
            price=price,
            part_number=part_number,
            raw_text=full_text[:2000],  # обрезаем, чтобы снимок не раздувался
        )
