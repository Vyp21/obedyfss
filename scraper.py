import re
import json
from curl_cffi import requests
from bs4 import BeautifulSoup

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

def parse_restaurant(res):
    try:
        # Vydává se za skutečný prohlížeč Chrome (obejde chyby 403 a 455)
        response = requests.get(res["url"], impersonate="chrome", timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.extract()

        lines = [line.strip() for line in soup.get_text(separator='\n').split('\n') if line.strip()]

        items = []
        current_day = "Týdenní nabídka"
        seen_meals = set()

        for i, line in enumerate(lines):
            lower_line = line.lower()

            day_found = False
            for key, day_name in DAYS_MAP.items():
                if key in lower_line and len(line) < 40:
                    current_day = day_name
                    day_found = True
                    break
            if day_found:
                continue

            price_match = PRICE_REGEX.search(line)
            if price_match:
                price = price_match.group(1)
                meal_name = PRICE_REGEX.sub('', line).strip(" -–:•\t")

                if len(meal_name) < 4 and i > 0:
                    prev_line = lines[i - 1]
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
                "name": "Menu se nepodařilo automaticky přečíst (může být v obrázku/PDF). Zkontrolujte web.",
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
                "name": f"Chyba při načítání webu: {e}",
                "price": ""
            }]
        }

def main():
    results = []
    for res in RESTAURANTS:
        print(f"Stahuji: {res['name']}...")
        results.append(parse_restaurant(res))

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
