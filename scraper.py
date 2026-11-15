import json
import re
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

DATA_FILE = "data/prices.json"
DAM_URL = "http://www.dam.gov.bd/site/page/24614873-8635-4838-8432-554695395735"

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
EN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

KEYWORDS = {
    "broiler": ["ব্রয়লার", "broiler"],
    "sonali": ["সোনালি", "সোনালী", "sonali"],
    "deshi-chicken": ["দেশি মুরগি", "দেশী মুরগি"],
    "farm-egg": ["ফার্মের ডিম", "মুরগির ডিম"],
    "duck-egg": ["হাঁসের ডিম"],
    "beef": ["গরুর মাংস"],
    "mutton": ["খাসির মাংস"],
    "rui": ["রুই"],
    "katla": ["কাতলা"],
    "pangas": ["পাঙ্গাস", "পাংগাস"],
    "tilapia": ["তেলাপিয়া"],
    "hilsha": ["ইলিশ"]
}


def get_bd_time():
    bd_tz = timezone(timedelta(hours=6))
    return datetime.now(bd_tz)


def format_bn_timestamp(dt):
    hour = dt.hour
    period = "সকাল" if hour < 12 else ("দুপুর" if hour < 16 else ("বিকাল" if hour < 18 else "রাত"))
    display_hour = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
    raw = f"{dt.strftime('%Y-%m-%d')} ({period} {display_hour}:{dt.strftime('%M')})"
    return raw.translate(BN_DIGITS)


def parse_price_range(text):
    clean = text.translate(EN_DIGITS)
    nums = [int(n) for n in re.findall(r"\d+", clean) if 20 <= int(n) <= 3000]
    if not nums:
        return None
    return round(sum(nums) / len(nums))


def is_valid_update(old_price, new_price):
    if not new_price or old_price <= 0:
        return False
    diff_ratio = abs(new_price - old_price) / old_price
    return diff_ratio <= 0.15


def fetch_dam_prices():
    scraped = {}
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DDBazarBot/1.0)"}
        resp = requests.get(DAM_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for row in soup.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            row_text = " ".join(cells)
            for item_id, terms in KEYWORDS.items():
                if any(term in row_text for term in terms):
                    prices = [parse_price_range(c) for c in cells[1:]]
                    prices = [p for p in prices if p is not None]
                    if prices:
                        scraped[item_id] = max(prices)
    except Exception as exc:
        print(f"DAM fetch skipped/fallback active: {exc}")
    return scraped


def update_prices():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    live_prices = fetch_dam_prices()
    now_bd = get_bd_time()

    if live_prices:
        dhaka_items = data["divisions"]["dhaka"]["items"]
        base_ratios = {}

        for item in dhaka_items:
            iid = item["id"]
            if iid in live_prices and is_valid_update(item["retail"], live_prices[iid]):
                old_retail = item["retail"]
                new_retail = live_prices[iid]
                ratio = new_retail / old_retail
                base_ratios[iid] = ratio
                item["change"] = new_retail - old_retail
                item["retail"] = new_retail
                item["wholesale"] = round(item["wholesale"] * ratio)

                if iid == "farm-egg":
                    for sub in dhaka_items:
                        if sub["id"] == "farm-egg-dozen":
                            sub["change"] = (new_retail * 3 - 4) - sub["retail"]
                            sub["retail"] = new_retail * 3 - 4
                            sub["wholesale"] = item["wholesale"] * 3 - 1

        for div_key, div_data in data["divisions"].items():
            if div_key == "dhaka":
                continue
            for item in div_data["items"]:
                iid = item["id"]
                if iid in base_ratios:
                    new_ret = round(item["retail"] * base_ratios[iid])
                    item["change"] = new_ret - item["retail"]
                    item["retail"] = new_ret
                    item["wholesale"] = round(item["wholesale"] * base_ratios[iid])

    data["meta"]["last_updated"] = format_bn_timestamp(now_bd)
    data["meta"]["iso_date"] = now_bd.isoformat()

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("prices.json updated successfully.")


if __name__ == "__main__":
    update_prices()
