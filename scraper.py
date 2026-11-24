import re
import json
import time
import urllib.parse
import requests

RESTAURANTS = [
    {"name": "La Famiglia", "url": "https://lafamigliabrno.cz/denni-menu"},
    {"name": "Desi Dhaba", "url": "https://desidhaba.cz/cs/"},
    {"name": "Naše Vaše Bistro", "url": "https://nasevasebistro.cz/denni-menu-2/"},
    {"name": "Ilegal Restaurant", "url": "https://www.ilegalrestaurant.cz"}
]

DAYS_MAP = {
    "pondělí": "Pondělí",
    "úterý": "Úterý",
    "středa": "Středa",
    "čtvrtek": "Čtvrtek",
    "pátek": "Pátek"
}

PRICE_REGEX = re.compile(r'(\d{2,4}(?:[.,]\d{1,2})?\s*(?:Kč|,-))', re.IGNORECASE)

def fetch_via_proxies(target_url):
    # 1. Pokus: Jina Reader (vykreslí stránku jako prohlížeč)
    try:
        r = requests.get(
            f"https://r.jina.ai/{target_url}",
            headers={"Accept": "text/plain", "X-Return-Format": "text"},
            timeout=25
        )
        if r.status_code == 200 and len(r.text) > 100:
            return r.text
    except Exception:
        pass

    # 2. Pokus: AllOrigins proxy (jiná IP adresa)
    try:
        encoded = urllib.parse.quote(target_url, safe='')
        r = requests.get(f"https://api.allorigins.win/raw?url={encoded}", timeout=25)
        if r.status_code == 200 and len(r.text) > 100:
            # Odstranění HTML značek
            clean = re.sub(r'<[^>]+>', '\n', r.text)
            return clean
    except Exception:
        pass

    raise Exception("Všechny metody stažení selhaly (web blokuje přístup ze serverů).")

def parse_restaurant(res):
    try:
        text = fetch_via_proxies(res["url"])
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        items = []
        current_day = "Týdenní nabídka"
        seen_meals = set()

        for i, line in enumerate(lines):
            lower_line = line.lower()

            day_found = False
            for key, day_name in DAYS_MAP.items():
                if key in lower_line and len(line) < 45:
                    current_day = day_name
                    day_found = True
                    break
            if day_found:
                continue

            price_match = PRICE_REGEX.search(line)
            if price_match:
                price = price_match.group(1)
                meal_name = PRICE_REGEX.sub('', line).strip(" -–:•|*#\t")

                if len(meal_name) < 4 and i > 0:
                    prev_line = lines[i - 1].strip(" -–:•|*#\t")
                    if not PRICE_REGEX.search(prev_line) and prev_line.lower() not in DAYS_MAP:
                        meal_name = prev_line

                if len(meal_name) >= 5 and meal_name not in seen_meals:
                    seen_meals.add(meal_name)
                    items.append({
                        "day": current_day,
                        "category": "",
                        "name": meal_name,
                        "price": price
                    })

        if not items:
            items.append({
                "day": "Týdenní nabídka",
                "category": "",
                "name": "Web se načetl, ale nenašly se ceny v Kč (menu může být v obrázku/PDF).",
                "price": ""
            })

        return {
            "restaurant": res["name"],
            "url": res["url"],
            "items": items
        }

    except Exception as e:
        return {
            "restaurant": res["name"],
            "url": res["url"],
            "items": [{
                "day": "Týdenní nabídka",
                "category": "",
                "name": f"Chyba: {e}",
                "price": ""
            }]
        }

def main():
    results = []
    for res in RESTAURANTS:
        print(f"Stahuji: {res['name']}...")
        results.append(parse_restaurant(res))
        time.sleep(2)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
