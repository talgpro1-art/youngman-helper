from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NOTI_FILE = ROOT / "data" / "notifications.json"
ROADMAP_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTTCzFCPz6nPFnu-oRoTjB16Ng7hhPAy811JU3DZcnSKglptFHHf3hLOVIXN4Y-yis7_RZhK52_Ys1m/pub?gid=1952505960&single=true&output=csv"
MAX_NEWS_AGE_DAYS = 7
BLOCKED_SOURCES = ("mshale", "naver blog", "네이버 블로그", "youtube", "유튜브", "gwaramedia", "바카라")


def now_kst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def safe_str(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def source_is_usable(value) -> bool:
    title = safe_str(value).lower()
    return bool(title) and not any(blocked in title for blocked in BLOCKED_SOURCES)


def empty_notification() -> list[dict]:
    return [{
        "date": now_kst().strftime("%Y-%m-%d"),
        "brand": "",
        "model": "",
        "title": "최근 검증 완료된 주요 신차/가격표 이슈가 없습니다.",
        "body": f"구글시트 검증 기준을 통과한 최근 {MAX_NEWS_AGE_DAYS}일 이내 신차·가격표 소식이 없습니다.",
        "link": "",
        "published": "",
        "severity": "info",
        "source": "newcar_watch_verified",
    }]


def load_verified_notifications() -> list[dict]:
    df = pd.read_csv(ROADMAP_URL)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    for column in ["status", "launch_confidence", "price_status", "source_title", "source_url", "source_date", "summary", "brand", "model", "vehicle"]:
        if column not in df.columns:
            df[column] = ""

    status = df["status"].fillna("").astype(str).str.strip().str.lower()
    confidence = df["launch_confidence"].fillna("").astype(str).str.strip().str.lower()
    price_status = df["price_status"].fillna("").astype(str).str.strip().str.lower()
    source_dt = pd.to_datetime(df["source_date"], errors="coerce", utc=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_NEWS_AGE_DAYS)

    mask = (
        status.isin(["recent", "upcoming"])
        & confidence.eq("confirmed")
        & price_status.isin(["available", "pending"])
        & source_dt.notna()
        & source_dt.ge(cutoff)
        & df["source_title"].map(source_is_usable)
    )
    selected = df.loc[mask].copy()
    if selected.empty:
        return []

    selected["_source_dt"] = source_dt[mask]
    selected["_vehicle_key"] = (
        selected["brand"].fillna("").astype(str)
        + "|"
        + selected["model"].fillna("").astype(str).where(
            selected["model"].fillna("").astype(str).str.strip().ne(""),
            selected["vehicle"].fillna("").astype(str),
        )
    ).str.lower().str.replace(r"[^0-9a-z가-힣]+", "", regex=True)

    selected = (
        selected.sort_values("_source_dt", ascending=False)
        .drop_duplicates("source_url")
        .drop_duplicates("_vehicle_key")
        .head(5)
    )

    notifications: list[dict] = []
    for _, row in selected.iterrows():
        article_dt = row["_source_dt"].tz_convert(timezone(timedelta(hours=9)))
        vehicle = safe_str(row.get("vehicle")) or f"{safe_str(row.get('brand'))} {safe_str(row.get('model'))}".strip()
        notifications.append({
            "date": article_dt.strftime("%Y-%m-%d"),
            "article_date": article_dt.strftime("%Y-%m-%d"),
            "brand": safe_str(row.get("brand")),
            "model": safe_str(row.get("model")),
            "vehicle": vehicle,
            "title": safe_str(row.get("source_title")) or vehicle,
            "body": safe_str(row.get("summary")),
            "link": safe_str(row.get("source_url")),
            "published": article_dt.isoformat(),
            "severity": "warning",
            "source": "newcar_watch_verified",
        })
    return notifications


def main() -> None:
    try:
        notifications = load_verified_notifications()
    except Exception as exc:
        print(f"Verified roadmap load failed: {exc}")
        notifications = []

    if not notifications:
        notifications = empty_notification()

    NOTI_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTI_FILE.write_text(json.dumps(notifications, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved notifications: {NOTI_FILE}")
    print(f"Count: {len(notifications)}")


if __name__ == "__main__":
    main()
