from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
NOTI_FILE = ROOT / "data" / "notifications.json"

IMPORTANT_KEYWORDS = [
    "신형", "출시", "사전계약", "가격표", "가격 인상", "가격 변경", "연식변경",
    "부분변경", "페이스리프트", "풀체인지", "카탈로그", "하이브리드", "전기차", "보조금", "출고",
]
EXCLUDE_KEYWORDS = ["중고차", "리스승계", "사고", "튜닝", "블랙박스", "롱텀", "비교해보니"]

def now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def safe_str(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text

def is_relevant_title(title: str, brand: str, model: str) -> bool:
    title_norm = title.replace(" ", "").lower()
    brand_norm = brand.replace(" ", "").lower()
    model_norm = model.replace(" ", "").lower()
    if not model_norm or model_norm not in title_norm:
        return False
    # 비교 대상 기사 제외: 예) 스타리아, 카니발보다 좋은 점
    if f"{model_norm}보다" in title_norm or f"{model_norm}대신" in title_norm:
        return False
    if any(keyword in title for keyword in EXCLUDE_KEYWORDS):
        return False
    if any(keyword in title for keyword in IMPORTANT_KEYWORDS):
        return True
    return bool(brand_norm and brand_norm in title_norm)

def fetch_news_for_vehicle(brand: str, model: str, limit: int = 1) -> list[dict]:
    query = f'"{brand} {model}" OR "{model}" 신형 출시 가격표 연식변경 사전계약'
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    results: list[dict] = []
    for entry in feed.entries[:30]:
        title = safe_str(entry.get("title", ""))
        link = safe_str(entry.get("link", ""))
        published = safe_str(entry.get("published", ""))
        if not is_relevant_title(title, brand, model):
            continue
        results.append({
            "date": now_date(),
            "brand": brand,
            "model": model,
            "title": title,
            "body": "신차/가격표/연식변경 관련 공개 뉴스 후보입니다. 상세 내용은 링크에서 확인해 주세요.",
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
            "title": "오늘 감지된 주요 신차/가격표 이슈가 없습니다.",
            "body": "TOP50 관련 주요 키워드 뉴스가 감지되지 않았습니다.",
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
