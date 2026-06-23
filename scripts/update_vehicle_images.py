from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).parent.name == "scripts" else Path(__file__).resolve().parent
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
REVIEW_FILE = ROOT / "data" / "vehicle_image_review.csv"

IMAGE_COLUMNS = ["image_url", "image_file", "image_source_url", "image_source_type", "image_review_status"]
ALLOWED_APPROVED_TYPES = {"official_newsroom", "official_site", "manual"}
BLOCKED_IMAGE_HOSTS = ("wikimedia.org", "wikipedia.org")


def safe_text(value: object) -> str:
    return str(value or "").strip()


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


def image_status(row: dict[str, str]) -> str:
    image_url = safe_text(row.get("image_url"))
    image_file = safe_text(row.get("image_file"))
    source_type = safe_text(row.get("image_source_type"))
    review_status = safe_text(row.get("image_review_status")).lower()

    if any(host in image_url.lower() for host in BLOCKED_IMAGE_HOSTS):
        return "rejected_blocked_source"
    if any(host in safe_text(row.get("image_source_url")).lower() for host in BLOCKED_IMAGE_HOSTS):
        return "rejected_blocked_source"
    if not image_url and not image_file:
        return "missing"
    if review_status != "approved":
        return "needs_review"
    if source_type not in ALLOWED_APPROVED_TYPES:
        return "needs_source_type"
    return "approved"


def write_review(rows: list[dict[str, str]]) -> None:
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "vehicle",
        "status",
        "image_url",
        "image_file",
        "image_source_url",
        "image_source_type",
        "image_review_status",
        "recommended_action",
    ]
    review_rows = []
    for row in rows:
        status = image_status(row)
        if status == "approved":
            action = "ready"
        elif status == "missing":
            action = "add official_newsroom or official_site image URL"
        elif status == "rejected_blocked_source":
            action = "remove blocked source and replace with official/manual URL"
        elif status == "needs_source_type":
            action = "set image_source_type to official_newsroom, official_site, or manual"
        else:
            action = "review image, then set image_review_status to approved"

        review_rows.append(
            {
                "rank": safe_text(row.get("rank")),
                "vehicle": safe_text(row.get("vehicle")) or f"{safe_text(row.get('brand'))} {safe_text(row.get('model'))}".strip(),
                "status": status,
                "image_url": safe_text(row.get("image_url")),
                "image_file": safe_text(row.get("image_file")),
                "image_source_url": safe_text(row.get("image_source_url")),
                "image_source_type": safe_text(row.get("image_source_type")),
                "image_review_status": safe_text(row.get("image_review_status")),
                "recommended_action": action,
            }
        )

    with REVIEW_FILE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(review_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and validate manually approved vehicle image URLs.")
    parser.add_argument("--write", action="store_true", help="Write missing image columns back to vehicle_master.csv.")
    args = parser.parse_args()

    rows, fieldnames = read_rows()
    if args.write:
        write_rows(rows, fieldnames)
    write_review(rows)

    print(f"review file: {REVIEW_FILE}")
    print("Only image_review_status=approved with official_newsroom, official_site, or manual sources is shown in the app.")


if __name__ == "__main__":
    main()
