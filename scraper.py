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
# Hledá odkazy na obrázky ve formátu Markdown ![alt](url) nebo přímé URL obrázků
IMG_REGEX = re.compile(r'(?:!\[.*?\]\((https?://[^\s\)]+\.(?:jpg|jpeg|png|webp)[^\s\)]*)\)|(https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)[^\s"\'<>]*))', re.IGNORECASE)

def fetch_via_proxies(target_url):
    # 1. Pokus: Jina Reader (vrací text včetně odkazů na obrázky v Markdownu)
    try:
        r = requests.get(
            f"https://r.jina.ai/{target_url}",
            headers={"Accept": "text/plain"},
            timeout=25
        )
        if r.status_code == 200 and len(r.text) > 100:
            return r.text
    except Exception:
        pass

    # 2. Pokus: AllOrigins proxy
    try:
        encoded = urllib.parse.quote(target_url, safe='')
        r = requests.get(f"https://api.allorigins.win/raw?url={encoded}", timeout=25)
        if r.status_code == 200 and len(r.text) > 100:
            return r.text
    except Exception:
        pass

    raise Exception("Všechny metody stažení selhaly.")

def extract_images(text):
    images = []
    ignore_words = ['logo', 'icon', 'flag', 'vlajka', 'avatar', 'facebook', 'instagram', 'tripadvisor']
    for match in IMG_REGEX.findall(text):
        img_url = match[0] or match[1]
        if img_url and not any(w in img_url.lower() for w in ignore_words):
            if img_url not in images:
                images.append(img_url)
    return images[:3]  # Maximálně 3 hlavní obrázky ze stránky

def parse_restaurant(res):
    try:
        text = fetch_via_proxies(res["url"])
        # Odstranění HTML značek pro čistší čtení řádků, ale zachování Markdown odkazů
        clean_text = re.sub(r'<[^>]+>', '\n', text)
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]

        items = []
        images = []
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

        # Pokud se nenašla žádná textová jídla, zkusíme najít obrázek s menu
        if not items:
            images = extract_images(text)
            if not images:
                items.append({
                    "day": "Týdenní nabídka",
                    "category": "",
                    "name": "Menu se nepodařilo automaticky načíst. Zkontrolujte web restaurace.",
                    "price": ""
                })

        return {
            "restaurant": res["name"],
            "url": res["url"],
            "items": items,
            "images": images
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
            }],
            "images": []
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
