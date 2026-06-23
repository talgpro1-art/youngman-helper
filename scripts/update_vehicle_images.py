from __future__ import annotations

import argparse
import csv
import json
import re
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).parent.name == "scripts" else Path(__file__).resolve().parent
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
CAR_IMAGE_DIR = ROOT / "assets" / "cars"
REVIEW_FILE = ROOT / "data" / "vehicle_image_review.csv"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "YoungmanHelper/1.0 (vehicle image updater)"

IMAGE_COLUMNS = ["image_url", "image_file", "image_source_url", "image_review_status"]


def safe_text(value: object) -> str:
    return str(value or "").strip()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^0-9a-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "vehicle"


def open_url(request: Request, timeout: int):
    try:
        return urlopen(request, timeout=timeout)
    except Exception as exc:
        if isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError):
            return urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
        raise


def api_json(params: dict[str, str | int]) -> dict:
    query = urlencode({"format": "json", "formatversion": "2", **params})
    request = Request(f"{COMMONS_API}?{query}", headers={"User-Agent": USER_AGENT})
    with open_url(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def find_commons_image(vehicle_name: str, brand: str, model: str) -> dict[str, str] | None:
    queries = [
        f'"{brand} {model}" car',
        f'"{vehicle_name}" car',
        f"{brand} {model} automobile",
    ]
    for query in queries:
        data = api_json(
            {
                "action": "query",
                "generator": "search",
                "gsrnamespace": 6,
                "gsrsearch": query,
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata",
                "iiurlwidth": 900,
            }
        )
        pages = data.get("query", {}).get("pages", [])
        for page in pages:
            imageinfo = (page.get("imageinfo") or [{}])[0]
            mime = safe_text(imageinfo.get("mime"))
            image_url = safe_text(imageinfo.get("thumburl") or imageinfo.get("url"))
            source_url = safe_text(imageinfo.get("descriptionurl") or imageinfo.get("url"))
            if image_url and mime.startswith("image/"):
                return {
                    "title": safe_text(page.get("title")),
                    "image_url": image_url,
                    "source_url": source_url,
                    "mime": mime,
                    "query": query,
                }
        time.sleep(0.3)
    return None


def extension_from_mime(mime: str, url: str) -> str:
    if "png" in mime:
        return ".png"
    if "webp" in mime:
        return ".webp"
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def download(url: str, path: Path) -> None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with open_url(request, timeout=40) as response:
        path.write_bytes(response.read())


def read_rows() -> tuple[list[dict[str, str]], list[str]]:
    with VEHICLE_MASTER.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    for column in IMAGE_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
        for row in rows:
            row.setdefault(column, "")
    return rows, fieldnames


def write_rows(rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with VEHICLE_MASTER.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_review_rows(review_rows: list[dict[str, str]]) -> None:
    review_fields = ["rank", "vehicle", "status", "image_file", "source_url", "commons_title", "query"]
    with REVIEW_FILE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_fields)
        writer.writeheader()
        writer.writerows(review_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download candidate vehicle images into assets/cars.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of vehicles to process.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing image_file values.")
    parser.add_argument("--download", action="store_true", help="Download images into assets/cars instead of only storing remote image_url values.")
    parser.add_argument("--dry-run", action="store_true", help="Only print candidates; do not download or update CSV.")
    args = parser.parse_args()

    rows, fieldnames = read_rows()
    CAR_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)

    review_rows: list[dict[str, str]] = []
    processed = 0
    for row in rows:
        if processed >= args.limit:
            break
        if (safe_text(row.get("image_url")) or safe_text(row.get("image_file"))) and not args.overwrite:
            continue

        rank = safe_text(row.get("rank"))
        brand = safe_text(row.get("brand"))
        model = safe_text(row.get("model"))
        vehicle_name = safe_text(row.get("vehicle")) or f"{brand} {model}".strip()
        print(f"[{rank}] searching {vehicle_name}")

        try:
            candidate = find_commons_image(vehicle_name, brand, model)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            row["image_review_status"] = f"error:{exc.__class__.__name__}"
            review_rows.append({"rank": rank, "vehicle": vehicle_name, "status": row["image_review_status"]})
            processed += 1
            if not args.dry_run:
                write_rows(rows, fieldnames)
                write_review_rows(review_rows)
            time.sleep(2.0)
            continue

        if not candidate:
            row["image_review_status"] = "not_found"
            review_rows.append({"rank": rank, "vehicle": vehicle_name, "status": "not_found"})
            processed += 1
            if not args.dry_run:
                write_rows(rows, fieldnames)
                write_review_rows(review_rows)
            continue

        if args.dry_run:
            status = "candidate_only"
            relative_path = ""
        else:
            row["image_url"] = candidate["image_url"]
            row["image_source_url"] = candidate["source_url"]
            row["image_review_status"] = "needs_review"
            relative_path = ""
            status = "linked"

            if args.download:
                ext = extension_from_mime(candidate["mime"], candidate["image_url"])
                filename = f"{int(rank):02d}_{slugify(brand)}_{slugify(model)}{ext}" if rank.isdigit() else f"{slugify(vehicle_name)}{ext}"
                relative_path = f"assets/cars/{filename}"
                target = ROOT / relative_path
                if not target.exists():
                    download(candidate["image_url"], target)
                row["image_file"] = relative_path
                status = "downloaded"

        review_rows.append(
            {
                "rank": rank,
                "vehicle": vehicle_name,
                "status": status,
                "image_file": relative_path,
                "source_url": candidate["source_url"],
                "commons_title": candidate["title"],
                "query": candidate["query"],
            }
        )
        processed += 1
        if not args.dry_run:
            write_rows(rows, fieldnames)
            write_review_rows(review_rows)
        time.sleep(1.0)

    if not args.dry_run:
        write_rows(rows, fieldnames)
    write_review_rows(review_rows)

    print(f"review file: {REVIEW_FILE}")
    print("next: review downloaded images, then change image_review_status to approved where correct.")


if __name__ == "__main__":
    main()
