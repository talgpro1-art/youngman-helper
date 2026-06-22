from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
NOTI_FILE = ROOT / "data" / "notifications.json"
SNAPSHOT_DIR = ROOT / "data" / "sales_snapshot"
HISTORY_DIR = SNAPSHOT_DIR / "history"
UPDATE_NOTIFICATIONS = ROOT / "scripts" / "update_notifications.py"
CHECK_PRICE_LINKS = ROOT / "scripts" / "check_price_links.py"


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def normalize_key(value: Any) -> str:
    return "".join(safe_str(value).lower().split())


def parse_units(value: Any) -> str:
    text = safe_str(value)
    if not text:
        return ""
    digits = text.replace(",", "")
    if digits.isdigit():
        return f"{int(digits):,}"
    return text


def parse_rank(value: Any) -> int | None:
    text = safe_str(value).replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def load_master() -> pd.DataFrame:
    if not VEHICLE_MASTER.exists():
        raise FileNotFoundError(f"vehicle_master.csv not found: {VEHICLE_MASTER}")
    df = pd.read_csv(VEHICLE_MASTER)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    if "rank" in df.columns:
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(999).astype(int)
    return df


def load_source(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"source file not found: {path}")
    src = pd.read_csv(path)
    src.columns = [c.replace("\ufeff", "").strip() for c in src.columns]

    required = {"brand", "model"}
    missing = required - set(src.columns)
    if missing:
        raise ValueError(f"source file missing required columns: {sorted(missing)}")

    if "rank" not in src.columns and "units_sold" not in src.columns:
        raise ValueError("source file needs at least 'rank' or 'units_sold' to build ordering")

    src["brand_norm"] = src["brand"].map(normalize_key)
    src["model_norm"] = src["model"].map(normalize_key)
    if "vehicle" not in src.columns:
        src["vehicle"] = src["brand"].astype(str).str.strip() + " " + src["model"].astype(str).str.strip()
    src["vehicle_norm"] = src["vehicle"].map(normalize_key)
    src["rank_num"] = src["rank"].map(parse_rank) if "rank" in src.columns else None
    src["units_num"] = src["units_sold"].map(parse_rank) if "units_sold" in src.columns else None
    return src


def build_lookup(df: pd.DataFrame) -> dict[tuple[str, str], list[int]]:
    lookup: dict[tuple[str, str], list[int]] = {}
    for idx, row in df.iterrows():
        key = (normalize_key(row.get("brand")), normalize_key(row.get("model")))
        lookup.setdefault(key, []).append(idx)
        vehicle_key = (normalize_key(row.get("vehicle")), "")
        lookup.setdefault(vehicle_key, []).append(idx)
    return lookup


def resolve_lookup(master: pd.DataFrame, indices: list[int], used: set[int]) -> int | None:
    if not indices:
        return None

    unique_indices = []
    seen = set()
    for idx in indices:
        if idx in seen or idx in used:
            continue
        seen.add(idx)
        unique_indices.append(idx)

    def sort_key(idx: int) -> tuple[int, int, int]:
        active = safe_str(master.at[idx, "active"]).upper() == "Y"
        rank = parse_rank(master.at[idx, "rank"]) or 999
        return (0 if active else 1, rank, idx)

    return sorted(unique_indices, key=sort_key)[0]


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    defaults = {
        "rank": 999,
        "rank_change": "-",
        "brand": "",
        "model": "",
        "vehicle": "",
        "units_sold": "업데이트 예정",
        "segment": "",
        "powertrain": "",
        "target_tag": "",
        "image_url": "",
        "price_url": "",
        "catalog_url": "",
        "active": "Y",
        "note": "",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


def rank_change(old_rank: Any, new_rank: int | None) -> str:
    old = parse_rank(old_rank)
    if old is None or new_rank is None:
        return "-"
    diff = old - new_rank
    if diff == 0:
        return "-"
    return f"{diff:+d}"


def update_master(master: pd.DataFrame, source: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    master = ensure_columns(master.copy())
    master["rank"] = pd.to_numeric(master["rank"], errors="coerce").fillna(999).astype(int)
    lookup = build_lookup(master)
    matched_rows: set[int] = set()
    used_rows: set[int] = set()
    changes: list[dict] = []

    if source["rank_num"].notna().any():
        ordered_source = source.sort_values(["rank_num", "brand", "model"], na_position="last")
    elif source["units_num"].notna().any():
        ordered_source = source.sort_values(["units_num", "brand", "model"], ascending=[False, True, True], na_position="last")
    else:
        ordered_source = source.sort_values(["brand", "model"])

    for new_rank, (_, src) in enumerate(ordered_source.iterrows(), start=1):
        brand_norm = safe_str(src.get("brand_norm"))
        model_norm = safe_str(src.get("model_norm"))
        vehicle_norm = safe_str(src.get("vehicle_norm"))
        candidate_indices: list[int] = []
        candidate_indices.extend(lookup.get((brand_norm, model_norm), []))
        candidate_indices.extend(lookup.get((vehicle_norm, ""), []))
        idx = resolve_lookup(master, candidate_indices, used_rows)
        if idx is None:
            continue

        matched_rows.add(idx)
        used_rows.add(idx)
        old_rank = master.at[idx, "rank"]
        master.at[idx, "rank"] = new_rank
        if "rank_num" in src and pd.notna(src.get("rank_num")):
            master.at[idx, "rank"] = int(src.get("rank_num"))
        if "units_sold" in src:
            master.at[idx, "units_sold"] = parse_units(src.get("units_sold")) or "업데이트 예정"
        master.at[idx, "rank_change"] = rank_change(old_rank, int(master.at[idx, "rank"]))
        master.at[idx, "active"] = "Y"

        changes.append(
            {
                "brand": safe_str(src.get("brand")),
                "model": safe_str(src.get("model")),
                "vehicle": safe_str(master.at[idx, "vehicle"]) or f"{safe_str(src.get('brand'))} {safe_str(src.get('model'))}".strip(),
                "old_rank": parse_rank(old_rank),
                "new_rank": int(master.at[idx, "rank"]),
                "rank_change": master.at[idx, "rank_change"],
                "units_sold": safe_str(master.at[idx, "units_sold"]),
            }
        )

    untouched = master.index.difference(pd.Index(sorted(matched_rows)))
    if len(untouched) > 0:
        tail_start = max([parse_rank(v) or 0 for v in master.loc[list(matched_rows), "rank"].tolist()] or [0]) + 1
        for offset, idx in enumerate(untouched, start=0):
            if parse_rank(master.at[idx, "rank"]) == 999:
                master.at[idx, "rank"] = tail_start + offset
            if safe_str(master.at[idx, "units_sold"]) in {"", "업데이트 예정"}:
                master.at[idx, "units_sold"] = "업데이트 예정"
            if safe_str(master.at[idx, "rank_change"]) in {"", "업데이트 필요"}:
                master.at[idx, "rank_change"] = "-"

    master = master.sort_values(["rank", "brand", "model"]).reset_index(drop=True)
    return master, changes


def append_notification(changes: list[dict], source_name: str) -> None:
    if not changes:
        return

    top_changes = [c for c in changes if parse_rank(c.get("new_rank")) is not None][:5]
    if not top_changes:
        return

    try:
        existing = json.loads(NOTI_FILE.read_text(encoding="utf-8")) if NOTI_FILE.exists() else []
    except Exception:
        existing = []

    body_parts = []
    for item in top_changes[:3]:
        vehicle = safe_str(item.get("vehicle"))
        old_rank = item.get("old_rank")
        new_rank = item.get("new_rank")
        if old_rank is None:
            body_parts.append(f"{vehicle} {new_rank}위 반영")
        else:
            body_parts.append(f"{vehicle} {old_rank}위 -> {new_rank}위")

    note = {
        "date": today_key(),
        "brand": "",
        "model": "",
        "title": "국내 판매순위 월간 업데이트",
        "body": f"{source_name} 기준으로 순위와 판매대수를 갱신했습니다. " + ", ".join(body_parts) + ".",
        "link": "",
        "severity": "info",
        "source": "sales_rank_updater",
    }
    merged = [note] + existing
    NOTI_FILE.write_text(json.dumps(merged[:15], ensure_ascii=False, indent=2), encoding="utf-8")


def run_post_tasks() -> None:
    tasks = [UPDATE_NOTIFICATIONS, CHECK_PRICE_LINKS]
    for task in tasks:
        if not task.exists():
            continue
        print(f"Running downstream task: {task.name}")
        subprocess.run([sys.executable, str(task)], check=True)


def save_outputs(master: pd.DataFrame, source: pd.DataFrame, source_path: Path) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    master.to_csv(VEHICLE_MASTER, index=False, encoding="utf-8-sig")
    source_out = HISTORY_DIR / f"sales_input_{today_key()}.csv"
    master_out = HISTORY_DIR / f"vehicle_master_{today_key()}.csv"
    source.to_csv(source_out, index=False, encoding="utf-8-sig")
    master.to_csv(master_out, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update vehicle_master.csv from a monthly sales ranking CSV.")
    parser.add_argument(
        "--input",
        required=True,
        help="Monthly sales CSV path with at least brand and model columns. Rank and units_sold are recommended.",
    )
    parser.add_argument(
        "--source-name",
        default="월간 판매집계",
        help="Displayed source name for notification text.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    source = load_source(input_path)
    master = load_master()
    updated, changes = update_master(master, source)
    save_outputs(updated, source, input_path)
    moved_changes = [item for item in changes if safe_str(item.get("rank_change")) != "-"]
    if moved_changes:
        append_notification(moved_changes, args.source_name)
        run_post_tasks()
    print(f"Updated vehicle_master.csv from {input_path}")
    print(f"Matched rows: {len(changes)}")
    print(f"Snapshot saved at: {HISTORY_DIR}")
    if not moved_changes:
        print("No rank changes detected; downstream tasks skipped.")


if __name__ == "__main__":
    main()
