from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
NOTI_FILE = ROOT / "data" / "notifications.json"
MAX_NEWS_AGE_DAYS = 7


def u(value: str) -> str:
    return value.encode("ascii").decode("unicode_escape")


IMPORTANT_KEYWORDS = [
    u("\\uc2e0\\ud615"), u("\\ucd9c\\uc2dc"), u("\\uc0ac\\uc804\\uacc4\\uc57d"), u("\\uac00\\uaca9\\ud45c"),
    u("\\uac00\\uaca9 \\uc778\\uc0c1"), u("\\uac00\\uaca9 \\ubcc0\\uacbd"), u("\\uc5f0\\uc2dd\\ubcc0\\uacbd"),
    u("\\ubd80\\ubd84\\ubcc0\\uacbd"), u("\\ud398\\uc774\\uc2a4\\ub9ac\\ud504\\ud2b8"), u("\\ud480\\uccb4\\uc778\\uc9c0"),
    u("\\uce74\\ud0c8\\ub85c\\uadf8"), u("\\ud558\\uc774\\ube0c\\ub9ac\\ub4dc"), u("\\uc804\\uae30\\ucc28"),
    u("\\ubcf4\\uc870\\uae08"), u("\\ucd9c\\uace0"),
]
EXCLUDE_KEYWORDS = [
    u("\\uc911\\uace0\\ucc28"), u("\\ub9ac\\uc2a4\\uc2b9\\uacc4"), u("\\uc0ac\\uace0"), u("\\ud29c\\ub2dd"),
    u("\\ube14\\ub799\\ubc15\\uc2a4"), u("\\ub871\\ud140"), u("\\ube44\\uad50\\ud574\\ubcf4\\ub2c8"),
]


def now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def safe_str(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def parse_published(value: str) -> datetime | None:
    text = safe_str(value)
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_recent_published(value: str, max_age_days: int = MAX_NEWS_AGE_DAYS) -> bool:
    published = parse_published(value)
    if published is None:
        return False
    return datetime.now(timezone.utc) - published <= timedelta(days=max_age_days)


def is_relevant_title(title: str, brand: str, model: str) -> bool:
    title_norm = title.replace(" ", "").lower()
    brand_norm = brand.replace(" ", "").lower()
    model_norm = model.replace(" ", "").lower()
    if not model_norm or model_norm not in title_norm:
        return False
    if f"{model_norm}{u('\\ubcf4\\ub2e4')}" in title_norm or f"{model_norm}{u('\\ub300\\uc2e0')}" in title_norm:
        return False
    if any(keyword in title for keyword in EXCLUDE_KEYWORDS):
        return False
    if any(keyword in title for keyword in IMPORTANT_KEYWORDS):
        return True
    return bool(brand_norm and brand_norm in title_norm)


def fetch_news_for_vehicle(brand: str, model: str, limit: int = 1) -> list[dict]:
    query = f'"{brand} {model}" OR "{model}" {u("\\uc2e0\\ud615 \\ucd9c\\uc2dc \\uac00\\uaca9\\ud45c \\uc5f0\\uc2dd\\ubcc0\\uacbd \\uc0ac\\uc804\\uacc4\\uc57d")}'
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    results: list[dict] = []
    seen_links: set[str] = set()
    for entry in feed.entries[:30]:
        title = safe_str(entry.get("title", ""))
        link = safe_str(entry.get("link", ""))
        published = safe_str(entry.get("published", ""))
        if link in seen_links:
            continue
        if not is_recent_published(published):
            continue
        article_dt = parse_published(published)
        if article_dt is None:
            continue
        if not is_relevant_title(title, brand, model):
            continue
        seen_links.add(link)
        results.append({
            # Show the publisher's date, never the collection run date.
            "date": article_dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"),
            "article_date": article_dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"),
            "collected_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
            "brand": brand,
            "model": model,
            "title": title,
            "body": u("\\ucd5c\\uadfc \\uc2e0\\ucc28/\\uac00\\uaca9\\ud45c/\\uc5f0\\uc2dd\\ubcc0\\uacbd \\uad00\\ub828 \\uacf5\\uac1c \\ub274\\uc2a4 \\ud6c4\\ubcf4\\uc785\\ub2c8\\ub2e4. \\uc0c1\\uc138 \\ub0b4\\uc6a9\\uc740 \\ub9c1\\ud06c\\uc5d0\\uc11c \\ud655\\uc778\\ud574 \\uc8fc\\uc138\\uc694."),
            "link": link,
            "published": published,
            "severity": "warning",
            "source": "google_news_rss",
        })
        if len(results) >= limit:
            break
    return results


def main() -> None:
    if not VEHICLE_MASTER.exists():
        print(f"vehicle_master.csv not found: {VEHICLE_MASTER}")
        return
    df = pd.read_csv(VEHICLE_MASTER)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    if "active" in df.columns:
        df = df[df["active"].astype(str).str.upper() == "Y"]
    notifications: list[dict] = []
    for _, row in df.head(20).iterrows():
        brand = safe_str(row.get("brand"))
        model = safe_str(row.get("model"))
        if not model:
            continue
        print(f"Checking news: {brand} {model}")
        notifications.extend(fetch_news_for_vehicle(brand, model, limit=1))
    if not notifications:
        notifications = [{
            "date": now_date(),
            "brand": "",
            "model": "",
            "title": u("\\ucd5c\\uadfc \\uac10\\uc9c0\\ub41c \\uc8fc\\uc694 \\uc2e0\\ucc28/\\uac00\\uaca9\\ud45c \\uc774\\uc288\\uac00 \\uc5c6\\uc2b5\\ub2c8\\ub2e4."),
            "body": u("\\ucd5c\\uadfc ") + str(MAX_NEWS_AGE_DAYS) + u("\\uc77c \\uc774\\ub0b4 TOP50 \\uad00\\ub828 \\uc8fc\\uc694 \\ud0a4\\uc6cc\\ub4dc \\ub274\\uc2a4\\uac00 \\uac10\\uc9c0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4."),
            "link": "",
            "published": "",
            "severity": "info",
            "source": "system",
        }]
    NOTI_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTI_FILE.write_text(json.dumps(notifications[:10], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved notifications: {NOTI_FILE}")
    print(f"Count: {len(notifications[:10])}")


if __name__ == "__main__":
    main()
