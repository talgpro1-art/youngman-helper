from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
LINK_STATUS = ROOT / "data" / "link_status.csv"
NOTI_FILE = ROOT / "data" / "notifications.json"
TIMEOUT = 25
BROWSER_ONLY_HOSTS = {
    "www.tesla.com",
    "www.mercedes-benz.co.kr",
    "www.audi.co.kr",
    "www.bmw.co.kr",
    "www.chevrolet.co.kr",
}

PRICE_LABEL = "\uac00\uaca9\ud45c"
EXTRA_PDF_LABEL = "\ucd94\uac00PDF"
NOTICE_TITLE = "\uacf5\uc2dd {doc_type} \ubcc0\uacbd \uac10\uc9c0: {vehicle}"
NOTICE_BODY = "\uacf5\uc2dd PDF/\uac00\uaca9\ud45c \ub9c1\ud06c\uc758 \ud30c\uc77c \ub0b4\uc6a9\uc774 \uc774\uc804 \uccb4\ud06c \ub300\ube44 \ubcc0\uacbd\ub418\uc5c8\uc2b5\ub2c8\ub2e4. \uc0c1\ub2f4 \uc804 \ucd5c\uc2e0 \uac00\uaca9\ud45c\ub97c \ud655\uc778\ud574 \uc8fc\uc138\uc694."


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_str(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_pdf_url(url: str) -> bool:
    return safe_str(url).split("?", 1)[0].split("#", 1)[0].lower().endswith(".pdf")


def browser_only_status(url: str) -> dict | None:
    host = urlparse(url).netloc.lower()
    if host in BROWSER_ONLY_HOSTS and not is_pdf_url(url):
        return {
            "status_code": 200,
            "content_type": "browser-only/html",
            "content_length": 0,
            "sha256": "",
            "last_modified": "",
            "etag": "",
        }
    return None


def fetch_hash(url: str) -> dict:
    browser_only = browser_only_status(url)
    if browser_only:
        return browser_only
    headers = {"User-Agent": "Mozilla/5.0 YoungmanHelper/1.0"}
    res = requests.get(url, headers=headers, timeout=TIMEOUT)
    content = res.content if res.ok and is_pdf_url(url) else b""
    return {
        "status_code": res.status_code,
        "content_type": res.headers.get("Content-Type", ""),
        "content_length": len(content),
        "sha256": sha256_bytes(content) if content else "",
        "last_modified": res.headers.get("Last-Modified", ""),
        "etag": res.headers.get("ETag", ""),
    }


def load_old() -> dict[tuple[str, str], str]:
    if not LINK_STATUS.exists():
        return {}
    old_df = pd.read_csv(LINK_STATUS)
    old_df.columns = [c.replace("\ufeff", "").strip() for c in old_df.columns]
    return {
        (safe_str(r.get("vehicle")), safe_str(r.get("doc_type"))): safe_str(r.get("sha256"))
        for _, r in old_df.iterrows()
    }


def append_notifications(changed_items: list[dict]) -> None:
    if not changed_items:
        return
    try:
        existing = json.loads(NOTI_FILE.read_text(encoding="utf-8")) if NOTI_FILE.exists() else []
    except Exception:
        existing = []
    new_items = []
    for item in changed_items[:10]:
        new_items.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "brand": item["brand"],
            "model": item["model"],
            "title": NOTICE_TITLE.format(doc_type=item["doc_type"], vehicle=item["vehicle"]),
            "body": NOTICE_BODY,
            "link": item["url"],
            "severity": "warning",
            "source": "price_link_checker",
        })
    NOTI_FILE.write_text(json.dumps((new_items + existing)[:15], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not VEHICLE_MASTER.exists():
        print(f"vehicle_master.csv not found: {VEHICLE_MASTER}")
        return
    df = pd.read_csv(VEHICLE_MASTER)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    old_hashes = load_old()
    rows = []
    changed = []
    for _, r in df.iterrows():
        brand = safe_str(r.get("brand"))
        model = safe_str(r.get("model"))
        vehicle = safe_str(r.get("vehicle")) or f"{brand} {model}".strip()
        for doc_type, col in [(PRICE_LABEL, "price_url"), (EXTRA_PDF_LABEL, "catalog_url")]:
            url = safe_str(r.get(col))
            if not url.startswith("http"):
                continue
            print(f"Checking {vehicle} {doc_type}: {url}")
            info = {"status_code": "ERROR", "content_type": "", "content_length": 0, "sha256": "", "last_modified": "", "etag": ""}
            error = ""
            try:
                info = fetch_hash(url)
            except Exception as e:
                error = str(e)
            old_sha = old_hashes.get((vehicle, doc_type), "")
            is_changed = bool(old_sha and info.get("sha256") and old_sha != info.get("sha256"))
            row = {
                "checked_at": now(),
                "rank": safe_str(r.get("rank")),
                "brand": brand,
                "model": model,
                "vehicle": vehicle,
                "doc_type": doc_type,
                "url": url,
                "changed": "Y" if is_changed else "N",
                "old_sha256": old_sha,
                "error": error,
                **info,
            }
            rows.append(row)
            if is_changed:
                changed.append(row)
    out = pd.DataFrame(rows)
    LINK_STATUS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(LINK_STATUS, index=False, encoding="utf-8-sig")
    append_notifications(changed)
    print(f"Saved link status: {LINK_STATUS}")
    print(f"Changed links: {len(changed)}")


if __name__ == "__main__":
    main()
