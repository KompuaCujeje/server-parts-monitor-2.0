# departments/server_parts/parsers/regard.py  (ДИАГНОСТИЧЕСКАЯ версия — замени этим текущий файл)
#
# Добавлены print()-сообщения на каждом шаге, чтобы в логе GitHub Actions
# было видно, что именно происходит: сколько ссылок нашли, что вернул сайт,
# почему карточка не распозналась. Это временная версия для отладки.

from .base import BaseParser, ProductSnapshot

KNOWN_PART_NUMBERS = ["MZ7L33T8HBLT-00A07", "MZ7L33T8HBLT"]


class RegardParser(BaseParser):
    source_id = "regard"

    def parse_listing_page(self, url: str, category: str) -> list[str]:
        soup = self.fetch(url)

        raw_length = len(str(soup))
        print(f"[regard][{category}] длина полученного HTML: {raw_length} символов")

        all_links = soup.find_all("a", href=True)
        print(f"[regard][{category}] всего ссылок <a> на странице: {len(all_links)}")

        links = []
        for a_tag in all_links:
            href = a_tag["href"]
            if "/product/" in href:
                full_url = href if href.startswith("http") else self.base_url + href
                if full_url not in links:
                    links.append(full_url)

        print(f"[regard][{category}] найдено ссылок на карточки товара (/product/): {len(links)}")
        if links:
            print(f"[regard][{category}] пример первой ссылки: {links[0]}")
        else:
            # Покажем первые 500 символов HTML, чтобы понять, что вообще пришло
            print(f"[regard][{category}] HTML не содержит /product/ ссылок. Начало ответа сайта:")
            print(str(soup)[:500])

        return links

    def parse_product_page(self, url: str, category: str) -> ProductSnapshot | None:
        soup = self.fetch(url)

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        price_tag = soup.find(attrs={"itemprop": "price"}) or soup.find(class_=lambda c: c and "price" in c.lower())
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price = self.extract_price(price_text)

        if not title or price is None:
            print(f"[regard][{category}] НЕ РАСПОЗНАНО: url={url}")
            print(f"[regard][{category}]   title_tag найден: {title_tag is not None}, текст title: '{title}'")
            print(f"[regard][{category}]   price_tag найден: {price_tag is not None}, текст price: '{price_text}'")
            return None

        full_text = soup.get_text(" ", strip=True)
        part_number = None
        if category == "disk":
            part_number = self.extract_part_number(full_text, KNOWN_PART_NUMBERS)

        print(f"[regard][{category}] OK: '{title}' — {price} ₽")

        return ProductSnapshot(
            source_id=self.source_id,
            category=category,
            url=url,
            title=title,
            price=price,
            part_number=part_number,
            raw_text=full_text[:2000],
        )
