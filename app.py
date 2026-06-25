from __future__ import annotations

from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
OPTION_SUMMARY = ROOT / "data" / "option_summary.csv"
OPTION_MENTIONS = ROOT / "data" / "option_mentions.csv"
NEWCAR_ROADMAP = ROOT / "data" / "newcar_roadmap.csv"
NEWCAR_ROADMAP_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTTCzFCPz6nPFnu-oRoTjB16Ng7hhPAy811JU3DZcnSKglptFHHf3hLOVIXN4Y-yis7_RZhK52_Ys1m/pub?gid=1952505960&single=true&output=csv"
CAR_IMAGE_DIR = ROOT / "assets" / "cars"
HEADER_IMAGE = ROOT / "assets" / "header.png"
APP_ICON = ROOT / "assets" / "icon.png"

st.set_page_config(
    page_title="영맨 헬퍼",
    page_icon=Image.open(APP_ICON) if APP_ICON.exists() else "🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"],
    button[kind="header"][data-testid="baseButton-headerNoPadding"],
    button[data-testid="collapsedControl"] {
        display: none !important;
    }
    .block-container {
        padding-top: 3.2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 980px;
    }
    .main-title {
        font-size: 2.0rem;
        font-weight: 900;
        margin-bottom: 0.15rem;
        letter-spacing: -0.04em;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #6b7280;
        margin-bottom: 1rem;
        line-height: 1.45;
    }
    .mobile-section-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin: 1.1rem 0 0.55rem 0;
    }
    .noti-card {
        border-radius: 14px;
        border: 1px solid #fed7aa;
        border-left: 5px solid #f97316;
        background: #fff7ed;
        padding: 0.95rem 0.95rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 4px 14px rgba(124, 45, 18, 0.08);
    }
    .noti-topline {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin-bottom: 0.35rem;
        flex-wrap: wrap;
    }
    .alert-badge {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.17rem 0.5rem;
        font-size: 0.72rem;
        font-weight: 850;
        line-height: 1.2;
    }
    .alert-badge.notice {
        background: #e0f2fe;
        color: #075985;
    }
    .alert-badge.price {
        background: #fee2e2;
        color: #991b1b;
    }
    .alert-badge.newcar {
        background: #dcfce7;
        color: #166534;
    }
    .noti-title {
        font-size: 0.98rem;
        font-weight: 800;
        color: #9a3412;
        line-height: 1.35;
    }
    .noti-body {
        font-size: 0.88rem;
        color: #7c2d12;
        margin-top: 0.2rem;
        line-height: 1.4;
    }
    .noti-empty {
        border: 1px solid #d1d5db;
        background: #f9fafb;
        border-radius: 14px;
        padding: 0.9rem;
        color: #374151;
        font-weight: 750;
    }
    .premium-zone {
        border: 1px solid #bae6fd;
        border-radius: 16px;
        background: linear-gradient(180deg, #f0f9ff 0%, #ffffff 100%);
        padding: 1rem;
        margin: 0.9rem 0 0.85rem 0;
        box-shadow: 0 6px 18px rgba(14, 116, 144, 0.10);
    }
    .premium-head {
        display: flex;
        justify-content: space-between;
        gap: 0.7rem;
        align-items: flex-start;
        margin-bottom: 0.75rem;
    }
    .premium-title {
        font-size: 1.1rem;
        font-weight: 950;
        color: #0f172a;
        line-height: 1.3;
    }
    .premium-sub {
        color: #475569;
        font-size: 0.84rem;
        line-height: 1.45;
        margin-top: 0.2rem;
    }
    .premium-badge {
        display: inline-flex;
        align-items: center;
        white-space: nowrap;
        border-radius: 999px;
        background: #0f172a;
        color: white;
        padding: 0.25rem 0.6rem;
        font-size: 0.72rem;
        font-weight: 850;
    }
    .roadmap-card {
        border: 1px solid #e0f2fe;
        border-radius: 14px;
        background: #ffffff;
        padding: 0.85rem;
        margin-top: 0.55rem;
    }
    .roadmap-topline {
        display: flex;
        justify-content: space-between;
        gap: 0.7rem;
        align-items: flex-start;
    }
    .roadmap-car {
        font-size: 1.0rem;
        font-weight: 900;
        color: #111827;
        line-height: 1.3;
    }
    .roadmap-dday {
        border-radius: 999px;
        background: #ecfeff;
        color: #0e7490;
        padding: 0.18rem 0.48rem;
        font-size: 0.74rem;
        font-weight: 900;
        white-space: nowrap;
    }
    .roadmap-summary {
        color: #475569;
        font-size: 0.84rem;
        line-height: 1.45;
        margin-top: 0.35rem;
    }
    .roadmap-section-label {
        font-size: 0.82rem;
        font-weight: 900;
        color: #075985;
        margin: 0.7rem 0 0.3rem 0;
    }
    .vehicle-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.95rem;
        margin-bottom: 0.75rem;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
    }
    .vehicle-card-head {
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        align-items: flex-start;
    }
    .rank-badge {
        font-size: 1.45rem;
        font-weight: 900;
        color: #111827;
        letter-spacing: -0.04em;
        white-space: nowrap;
    }
    .rank-change {
        font-size: 0.85rem;
        font-weight: 700;
        color: #4b5563;
        margin-left: 0.25rem;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        background: #fef3c7;
        color: #92400e;
        padding: 0.16rem 0.48rem;
        font-size: 0.72rem;
        font-weight: 850;
        margin-left: 0.35rem;
        vertical-align: middle;
        white-space: nowrap;
    }
    .vehicle-name {
        font-size: 1.18rem;
        font-weight: 900;
        color: #111827;
        text-align: right;
        letter-spacing: -0.04em;
    }
    .vehicle-meta {
        color: #6b7280;
        font-size: 0.86rem;
        text-align: right;
        margin-top: 0.1rem;
        line-height: 1.35;
    }
    .car-placeholder {
        height: 120px;
        border-radius: 14px;
        background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.4rem;
        margin: 0.8rem 0 0.65rem 0;
    }
    .tag-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin: 0.55rem 0 0.7rem 0;
    }
    .pill {
        display: inline-block;
        border-radius: 999px;
        background: #f3f4f6;
        color: #374151;
        padding: 0.22rem 0.55rem;
        font-size: 0.76rem;
        font-weight: 700;
    }
    .pdf-button {
        display: block;
        width: 100%;
        text-align: center;
        padding: 0.78rem 0.72rem;
        border-radius: 12px;
        margin-top: 0.45rem;
        background: #111827;
        color: white !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: 0.92rem;
    }
    .pdf-button.secondary {
        background: #374151;
    }
    .pdf-button.disabled {
        background: #e5e7eb;
        color: #6b7280 !important;
        pointer-events: none;
        font-weight: 850;
    }
    .option-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.95rem;
        margin-bottom: 0.65rem;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .option-name {
        font-size: 1.0rem;
        font-weight: 850;
        margin-bottom: 0.35rem;
    }
    .option-label {
        display: inline-block;
        font-size: 0.74rem;
        font-weight: 850;
        color: #4b5563;
        background: #f3f4f6;
        border-radius: 999px;
        padding: 0.15rem 0.48rem;
        margin: 0.45rem 0 0.25rem 0;
    }
    .talking-point {
        border-left: 4px solid #2563eb;
        background: #eff6ff;
        padding: 0.65rem 0.72rem;
        border-radius: 10px;
        margin-top: 0.5rem;
        color: #1e3a8a;
        line-height: 1.45;
        font-size: 0.9rem;
    }
    .effect-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        background: #ffffff;
        padding: 0.95rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .effect-title {
        font-size: 0.98rem;
        font-weight: 900;
        color: #111827;
        margin-bottom: 0.35rem;
    }
    .effect-body {
        color: #4b5563;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .effect-list {
        margin: 0.35rem 0 0 1rem;
        padding: 0;
        color: #374151;
        line-height: 1.55;
        font-size: 0.9rem;
    }
    .demo-note {
        border: 1px solid #dbeafe;
        background: #eff6ff;
        border-radius: 14px;
        padding: 0.9rem;
        color: #1e3a8a;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-top: 0.75rem;
    }
    .small-muted {
        font-size: 0.82rem;
        color: #6b7280;
        line-height: 1.4;
    }
    div[data-testid="stMetric"] {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.65rem;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-top: 3.4rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        .main-title {font-size: 1.75rem;}
        .sub-title {font-size: 0.88rem;}
        .vehicle-card {padding: 0.85rem; border-radius: 16px;}
        .rank-badge {font-size: 1.28rem;}
        .vehicle-name {font-size: 1.05rem;}
        .car-placeholder {height: 92px;}
        .pdf-button {padding: 0.76rem 0.65rem; font-size: 0.9rem;}
        .noti-card {padding: 0.85rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_str(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def html_text(value: object, default: str = "") -> str:
    return escape(safe_str(value, default))


def display_units(value: object) -> str:
    text = safe_str(value)
    if not text or text == "업데이트 필요":
        return "업데이트 예정"
    return text


def display_rank_change(value: object) -> str:
    text = safe_str(value)
    if not text or text in {"-", "업데이트 필요"}:
        return "-"
    return text


def is_pdf_url(url: str) -> bool:
    clean = safe_str(url).split("?", 1)[0].split("#", 1)[0].lower()
    return clean.endswith(".pdf")


def is_hybrid_price_url(url: str) -> bool:
    clean = safe_str(url).lower()
    return "hybrid" in clean or "hev" in clean


def price_button_label(url: str, has_hybrid_pair: bool = False) -> str:
    if "genesis.com/kr/ko/support/download-center" in safe_str(url).lower():
        return "공홈 가격표/카탈로그 보기"
    if not is_pdf_url(url):
        return "공홈 가격표 보기"
    if is_hybrid_price_url(url):
        return "공식 가격표 보기(하이브리드)"
    if has_hybrid_pair:
        return "공식 가격표 보기(일반)"
    return "공식 가격표 보기"


def price_links(row: pd.Series) -> list[tuple[str, str, bool]]:
    urls = [safe_str(row.get("price_url")), safe_str(row.get("catalog_url"))]
    valid_urls: list[str] = []
    for url in urls:
        if url.startswith("http") and url not in valid_urls:
            valid_urls.append(url)

    has_hybrid_pair = any(is_hybrid_price_url(url) for url in valid_urls) and len(valid_urls) > 1
    return [(url, price_button_label(url, has_hybrid_pair), index > 0) for index, url in enumerate(valid_urls)]


def notification_badge(item: dict) -> tuple[str, str]:
    haystack = " ".join(
        [
            safe_str(item.get("title")),
            safe_str(item.get("body")),
            safe_str(item.get("source")),
            safe_str(item.get("vehicle")),
        ]
    ).lower()
    if any(key in haystack for key in ["가격", "pdf", "price", "링크"]):
        return "가격표", "price"
    if any(key in haystack for key in ["신차", "출시", "new"]):
        return "신차", "newcar"
    return "업무공지", "notice"


def consultation_sentence(vehicle_name: str, option_name: str, sales_point: str) -> str:
    if sales_point:
        return f"{vehicle_name} 상담에서는 '{option_name}'을 {sales_point} 관점으로 설명하면 좋습니다."
    return f"{vehicle_name} 상담에서는 '{option_name}'을 고객이 바로 체감할 수 있는 편의·안전 포인트로 설명하면 좋습니다."


def file_version(path: Path) -> int:
    if not path.exists():
        return 0
    return path.stat().st_mtime_ns


def vehicle_image_source(row: pd.Series) -> str | Path | None:
    review_status = safe_str(row.get("image_review_status")).lower()
    if review_status != "approved":
        return None

    image_file = safe_str(row.get("image_file"))
    if image_file:
        candidates = [
            ROOT / image_file,
            CAR_IMAGE_DIR / image_file,
            CAR_IMAGE_DIR / Path(image_file).name,
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

    image_url = safe_str(row.get("image_url"))
    if image_url.startswith("http"):
        return image_url
    return None


@st.cache_data(show_spinner=False)
def load_vehicles(version: int) -> pd.DataFrame:
    if not VEHICLE_MASTER.exists():
        return pd.DataFrame()

    df = pd.read_csv(VEHICLE_MASTER)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    defaults = {
        "rank": range(1, len(df) + 1),
        "rank_change": "-",
        "brand": "",
        "model": "",
        "vehicle": "",
        "units_sold": "업데이트 필요",
        "segment": "",
        "powertrain": "",
        "target_tag": "",
        "image_url": "",
        "image_file": "",
        "image_source_url": "",
        "image_source_type": "",
        "image_review_status": "",
        "price_url": "",
        "catalog_url": "",
        "active": "Y",
        "note": "",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = list(default) if col == "rank" else default

    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(999).astype(int)
    df["vehicle_name"] = df.apply(
        lambda r: safe_str(r.get("vehicle")) or f"{safe_str(r.get('brand'))} {safe_str(r.get('model'))}".strip(),
        axis=1,
    )
    df["has_price"] = df["price_url"].fillna("").astype(str).str.startswith("http")
    df["has_catalog"] = df["catalog_url"].fillna("").astype(str).str.startswith("http")
    df["has_pdf"] = df["has_price"] | df["has_catalog"]
    return df.sort_values("rank").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_options(version: int) -> pd.DataFrame:
    if not OPTION_SUMMARY.exists():
        return pd.DataFrame()
    df = pd.read_csv(OPTION_SUMMARY)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    return df

@st.cache_data(show_spinner=False, ttl=3600)
def load_newcar_roadmap(version: int = 0) -> pd.DataFrame:
    try:
        if NEWCAR_ROADMAP_URL:
            df = pd.read_csv(NEWCAR_ROADMAP_URL)
        elif NEWCAR_ROADMAP.exists():
            df = pd.read_csv(NEWCAR_ROADMAP)
        else:
            return pd.DataFrame()
    except Exception:
        if NEWCAR_ROADMAP.exists():
            df = pd.read_csv(NEWCAR_ROADMAP)
        else:
            return pd.DataFrame()

    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    df["launch_dt"] = pd.to_datetime(df.get("launch_date"), errors="coerce")
    df["priority"] = pd.to_numeric(df.get("priority"), errors="coerce").fillna(99).astype(int)
    return df

@st.cache_data(show_spinner=False)
def load_mentions(version: int) -> pd.DataFrame:
    if not OPTION_MENTIONS.exists():
        return pd.DataFrame()
    df = pd.read_csv(OPTION_MENTIONS)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    return df

def render_link_button(url: str, label: str, secondary: bool = False, disabled_label: str | None = None) -> None:
    url = safe_str(url)
    if url.startswith("http"):
        cls = "pdf-button secondary" if secondary else "pdf-button"
        st.markdown(f'<a href="{escape(url)}" target="_blank" class="{cls}">{html_text(label)}</a>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="pdf-button disabled">{html_text(disabled_label or f"{label} 없음")}</div>',
            unsafe_allow_html=True,
        )


def show_half_width_image(source: str | Path) -> None:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.image(source, width="stretch")


def dday_label(value: object) -> str:
    launch_dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(launch_dt):
        return "일정 확인"
    today = pd.Timestamp.today().normalize()
    diff = (launch_dt.normalize() - today).days
    if diff > 0:
        return f"D-{diff}"
    if diff == 0:
        return "D-Day"
    return f"D+{abs(diff)}"

def confidence_label(value: object) -> str:
    value = safe_str(value).lower()
    return {
        "confirmed": "공식 확인",
        "likely": "출시 유력",
        "rumor": "검증 필요",
    }.get(value, "확인중")


def price_status_label(value: object) -> str:
    value = safe_str(value).lower()
    return {
        "available": "가격표 있음",
        "pending": "가격표 대기",
        "none": "가격표 없음",
    }.get(value, "가격표 확인중")


def filtered_newcars(newcars: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if newcars.empty:
        return pd.DataFrame(), pd.DataFrame()

    today = pd.Timestamp.today().normalize()
    statuses = newcars.get("status", pd.Series([""] * len(newcars))).astype(str).str.lower()
    launch_dt = newcars.get("launch_dt", pd.Series([pd.NaT] * len(newcars)))

    upcoming = newcars[
        (statuses == "upcoming")
        & (launch_dt.notna())
        & (launch_dt >= today)
        & (launch_dt <= today + pd.Timedelta(days=60))
    ].copy()

    recent = newcars[
        (statuses == "recent")
        & (launch_dt.notna())
        & (launch_dt >= today - pd.Timedelta(days=14))
        & (launch_dt <= today)
    ].copy()

    return (
        upcoming.sort_values(["priority", "launch_dt"]).head(5),
        recent.sort_values(["priority", "launch_dt"], ascending=[True, False]).head(5),
    )


def show_newcar_premium_zone(newcars: pd.DataFrame) -> None:
    upcoming, recent = filtered_newcars(newcars)
    total = len(upcoming) + len(recent)
    html_parts = [
        f"""
        <div class="premium-zone">
            <div class="premium-head">
                <div>
                    <div class="premium-title">🚨 신차 출시 로드맵</div>
                    <div class="premium-sub">향후 60일 출시 예정 차량과 최근 2주 출시 차량의 가격표를 먼저 확인합니다.</div>
                </div>
                <div class="premium-badge">{total}건</div>
            </div>
        """
    ]

    if total == 0:
        html_parts.append(
            """
            <div class="roadmap-card">
                <div class="roadmap-car">업데이트 대기</div>
                <div class="roadmap-summary">현재 D+60 출시 예정 또는 최근 2주 내 출시 차량 데이터가 없습니다.</div>
            </div>
            """
        )
    else:
        if not upcoming.empty:
            html_parts.append('<div class="roadmap-section-label">출시 예정 D+60</div>')
            for _, row in upcoming.iterrows():
                vehicle = html_text(row.get("vehicle"), "신차")
                launch_date = html_text(row.get("launch_date"))
                summary = html_text(row.get("summary"), "출시 일정 확인 필요")
                confidence = html_text(confidence_label(row.get("launch_confidence")))
                price_status = html_text(price_status_label(row.get("price_status")))
                source_url = safe_str(row.get("source_url"))
                confidence = html_text(row.get("launch_confidence"), "확인중")
                price_status = html_text(row.get("price_status"), "pending")
                source_html = f'<div class="roadmap-summary"><a href="{escape(source_url)}" target="_blank">출처 확인</a></div>' if source_url.startswith("http") else ""
                html_parts.append(
                    f"""
                    <div class="roadmap-card">
                        <div class="roadmap-topline">
                            <div>
                                <div class="roadmap-car">{vehicle}</div>
                                <div class="small-muted">{launch_date} 출시 예정</div>
                            </div>
                            <div class="roadmap-dday">{html_text(dday_label(row.get("launch_dt")))}</div>
                        </div>
                        <div class="roadmap-summary">{summary}</div>
                        <div class="small-muted">출시 신뢰도: {confidence} · 가격표: {price_status}</div>
                        {source_html}
                    </div>
                    """
                )

        if not recent.empty:
            html_parts.append('<div class="roadmap-section-label">최근 출시 / 가격표</div>')
            for _, row in recent.iterrows():
                vehicle = html_text(row.get("vehicle"), "신차")
                launch_date = html_text(row.get("launch_date"))
                summary = html_text(row.get("summary"), "최근 출시 차량입니다.")
                confidence = html_text(confidence_label(row.get("launch_confidence")))
                price_status = html_text(price_status_label(row.get("price_status")))
                links_html = ""
                for url, label in [
                    (safe_str(row.get("price_url")), "신차 가격표 바로보기"),
                    (safe_str(row.get("catalog_url")), "신차 카탈로그 바로보기"),
                ]:
                    if url.startswith("http"):
                        cls = "pdf-button secondary" if "카탈로그" in label else "pdf-button"
                        links_html += f'<a href="{escape(url)}" target="_blank" class="{cls}">{html_text(label)}</a>'
                html_parts.append(
                    f"""
                    <div class="roadmap-card">
                        <div class="roadmap-topline">
                            <div>
                                <div class="roadmap-car">{vehicle}</div>
                                <div class="small-muted">{launch_date} 출시</div>
                            </div>
                            <div class="roadmap-dday">{html_text(dday_label(row.get("launch_dt")))}</div>
                        </div>
                        <div class="roadmap-summary">{summary}</div>
                        <div class="small-muted">출시 신뢰도: {confidence} · 가격표: {price_status}</div>
                        {links_html}
                    </div>
                    """
                )

    html_parts.append("</div>")
    roadmap_html = "\n".join(dedent(part).strip() for part in html_parts if safe_str(part))
    st.markdown(roadmap_html, unsafe_allow_html=True)


def filter_vehicles(df: pd.DataFrame) -> pd.DataFrame:
    search = st.text_input("차량명 검색", placeholder="예: 쏘렌토, 그랜저, 카니발")

    segments = ["전체"]
    if "segment" in df.columns:
        values = [safe_str(v) for v in df["segment"].dropna().unique().tolist()]
        segments += sorted([v for v in values if v])
    selected_segment = st.selectbox("차급 필터", segments, index=0)

    filtered = df.copy()
    if search.strip():
        key = search.strip().lower()
        filtered = filtered[filtered["vehicle_name"].str.lower().str.contains(key, na=False)]
    if selected_segment != "전체":
        filtered = filtered[filtered["segment"].astype(str) == selected_segment]

    return filtered.reset_index(drop=True)


def show_vehicle_card(row: pd.Series) -> None:
    name = safe_str(row.get("vehicle_name"))
    rank = safe_str(row.get("rank"))
    rank_change = display_rank_change(row.get("rank_change"))
    units = display_units(row.get("units_sold"))
    image_source = vehicle_image_source(row)
    price_url = safe_str(row.get("price_url"))
    catalog_url = safe_str(row.get("catalog_url"))
    segment = safe_str(row.get("segment"))
    powertrain = safe_str(row.get("powertrain"))
    target = safe_str(row.get("target_tag"))
    note = safe_str(row.get("note"))
    active = safe_str(row.get("active"), "Y").upper()
    links = price_links(row)
    status_html = '<span class="status-badge">확인 필요</span>' if active == "N" else ""

    st.markdown('<div class="vehicle-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="vehicle-card-head">
            <div>
                <span class="rank-badge">{html_text(rank)}위</span>
                <span class="rank-change">{html_text(rank_change)}</span>
            </div>
            <div>
                <div class="vehicle-name">{html_text(name)}{status_html}</div>
                <div class="vehicle-meta">{html_text(units)} · {html_text(segment or '차급 업데이트 예정')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if image_source:
        show_half_width_image(image_source)
    else:
        st.markdown('<div class="car-placeholder">🚗</div>', unsafe_allow_html=True)

    tags = [tag for tag in [segment, powertrain, target] if tag]
    if tags:
        tag_html = "".join([f'<span class="pill">{html_text(tag)}</span>' for tag in tags])
        st.markdown(f'<div class="tag-row">{tag_html}</div>', unsafe_allow_html=True)

    if links:
        for url, label, secondary in links:
            render_link_button(url, label, secondary=secondary)
    else:
        render_link_button("", "공식 가격표 보기", disabled_label="공식 PDF 확인 필요")

    if note:
        st.caption(f"비고: {note}")
    st.markdown("</div>", unsafe_allow_html=True)


def rank_table(df: pd.DataFrame) -> pd.DataFrame:
    table = df[["rank", "rank_change", "vehicle_name", "units_sold", "segment", "has_pdf", "active"]].copy()
    table["rank_change"] = table["rank_change"].apply(display_rank_change)
    table["units_sold"] = table["units_sold"].apply(display_units)
    table["has_pdf"] = table["has_pdf"].map(lambda ready: "있음" if ready else "확인 필요")
    table["active"] = table["active"].astype(str).str.upper().map(lambda value: "확인 필요" if value == "N" else "활성")
    table.columns = ["순위", "변동", "차량", "판매/등록대수", "차급", "공식링크", "상태"]
    return table


def show_summary_metrics(df: pd.DataFrame) -> None:
    total = len(df)
    official_ready = int(df["has_pdf"].sum()) if not df.empty else 0
    active_ready = int((df["active"].astype(str).str.upper() == "Y").sum()) if not df.empty else 0

    st.markdown('<div class="mobile-section-title">운영 데이터 요약</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("관리 차종", f"{total}개")
    m2.metric("공식링크", f"{official_ready}개")
    m3.metric("활성", f"{active_ready}개")


def show_rank_section(df: pd.DataFrame) -> None:
    st.markdown('<div class="mobile-section-title">🏆 국내 차량 판매 순위 TOP50</div>', unsafe_allow_html=True)
    st.dataframe(rank_table(df), width="stretch", hide_index=True, height=215)
    st.caption("표는 5위 정도만 보이도록 고정했습니다. 나머지 순위는 표 안에서 스크롤해 확인합니다.")

    filtered = filter_vehicles(df)
    st.caption(f"표시 차량: {len(filtered)}개")

    for _, row in filtered.iterrows():
        show_vehicle_card(row)


def show_pdf_section(df: pd.DataFrame) -> None:
    st.markdown('<div class="mobile-section-title">📄 공식 가격표·PDF 바로가기</div>', unsafe_allow_html=True)
    keyword = st.text_input("가격표 검색", placeholder="예: 쏘렌토, 그랜저, 카니발")

    filtered = df.copy()
    if keyword.strip():
        key = keyword.strip().lower()
        filtered = filtered[filtered["vehicle_name"].str.lower().str.contains(key, na=False)]

    for _, row in filtered.iterrows():
        with st.expander(f"{int(row['rank'])}위 · {row['vehicle_name']}"):
            st.write(f"**차급:** {safe_str(row.get('segment')) or '-'}  /  **영업 태그:** {safe_str(row.get('target_tag')) or '-'}")
            links = price_links(row)
            if links:
                for url, label, secondary in links:
                    render_link_button(url, label, secondary=secondary)
            else:
                render_link_button("", "공식 가격표 보기", disabled_label="공식 PDF 확인 필요")
            note = safe_str(row.get("note"))
            if note:
                st.caption(f"비고: {note}")


def show_option_section(df: pd.DataFrame, options: pd.DataFrame, mentions: pd.DataFrame) -> None:
    st.markdown('<div class="mobile-section-title">⭐ 차량별 관심 옵션·기능 설명</div>', unsafe_allow_html=True)
    st.caption(
        "TOP10 차량 중심으로 상담 문장을 먼저 보여줍니다. "
        "운영 시 공식 가격표와 안내 문구를 주기적으로 업데이트할 수 있습니다."
    )
    st.caption(
        "온라인 언급률은 커뮤니티·검색 반응을 운영 시 집계할 수 있도록 설계한 참고 지표입니다. "
        "현재 값은 TOP10 시연용 샘플 데이터입니다."
    )

    top10 = df[df["rank"] <= 10].copy()
    scope = st.radio("옵션 표시 범위", ["TOP10 데모", "전체 차량"], horizontal=True)
    choices = (top10 if scope == "TOP10 데모" and not top10.empty else df)["vehicle_name"].tolist()

    selected = st.selectbox("차량 선택", choices)
    row = df[df["vehicle_name"] == selected].iloc[0]

    brand = safe_str(row.get("brand"))
    model = safe_str(row.get("model"))
    vehicle_name = safe_str(row.get("vehicle_name"))

    matched = (
        options[
            (options["brand"].astype(str) == brand)
            & (options["model"].astype(str) == model)
        ]
        if not options.empty
        else pd.DataFrame()
    )

    if matched.empty:
        st.info("아직 옵션 설명 데이터가 없습니다.")
        return

    matched_mentions = (
        mentions[
            (mentions["brand"].astype(str) == brand)
            & (mentions["model"].astype(str) == model)
        ]
        if not mentions.empty
        else pd.DataFrame()
    )

    for _, opt in matched.iterrows():
        option_name = safe_str(opt.get("option_name"), "관심 옵션")
        function = safe_str(opt.get("function"), "차량 이용 편의성과 안전성을 높이는 기능")
        sales_point = safe_str(opt.get("sales_point"))
        talk = consultation_sentence(vehicle_name, option_name, sales_point)

        status = safe_str(opt.get("data_status"))
        status_html = f'<div class="small-muted">{html_text(status)}</div>' if status else ""

        mention_html = '<div class="small-muted">온라인 언급률 데이터는 아직 준비되지 않았습니다.</div>'
        if not matched_mentions.empty:
            mention_rows = matched_mentions[matched_mentions["option_name"].astype(str) == option_name]
            if not mention_rows.empty:
                mention = mention_rows.iloc[0]
                rate = safe_str(mention.get("mention_rate"), "0")
                count = safe_str(mention.get("mention_count"), "0")
                total = safe_str(mention.get("total_mentions"), "0")
                keywords = safe_str(mention.get("keywords")).replace(";", " · ")
                source_note = safe_str(mention.get("source_note"), "온라인 반응 참고 지표")
                mention_html = (
                    '<div style="border-radius:12px;background:#eef2ff;border:1px solid #c7d2fe;'
                    'padding:0.65rem 0.75rem;margin:0.55rem 0;">'
                    f'<div style="font-size:1.02rem;font-weight:900;color:#3730a3;">온라인 언급률 {html_text(rate)}%</div>'
                    f'<div style="font-size:0.82rem;color:#4338ca;">언급 수 {html_text(count)}/{html_text(total)} · {html_text(source_note)}</div>'
                    f'<div style="font-size:0.82rem;color:#4338ca;">주요 키워드: {html_text(keywords)}</div>'
                    '</div>'
                )

        card_html = (
            '<div class="option-card">'
            f'<div class="option-name">⭐ {html_text(option_name)}</div>'
            f'{mention_html}'
            '<div class="option-label">쉬운 설명</div>'
            f'<div class="effect-body">{html_text(function)}</div>'
            '<div class="option-label">고객에게 이렇게 설명</div>'
            f'<div class="talking-point">{html_text(talk)}</div>'
            f'{status_html}'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    st.info(
        "옵션명·설명은 영업 상담 보조용 요약입니다. "
        "실제 적용 트림, 옵션 구성, 가격은 반드시 공식 가격표를 확인하세요."
    )

def show_effect_section() -> None:
    st.markdown('<div class="mobile-section-title">📌 업무효과</div>', unsafe_allow_html=True)
    st.caption("영맨 헬퍼는 공개 자료 기반 정보를 한 화면에 모아 상담 준비 과정을 표준화합니다.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="effect-card">
                <div class="effect-title">기존 업무 방식</div>
                <ul class="effect-list">
                    <li>차량 판매순위 확인</li>
                    <li>브랜드별 가격표 검색</li>
                    <li>옵션 설명 별도 확인</li>
                    <li>신차/가격 변경 이슈 개별 확인</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="effect-card">
                <div class="effect-title">영맨 헬퍼 적용 후</div>
                <ul class="effect-list">
                    <li>TOP50 순위와 공식 가격표를 한 화면에서 확인</li>
                    <li>차량별 옵션 설명을 상담 문장으로 확인</li>
                    <li>주요 알림을 상단에서 빠르게 확인</li>
                    <li>공식/공개 자료 기반으로 보안 부담 최소화</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="mobile-section-title">기대효과</div>', unsafe_allow_html=True)
    effects = [
        ("영업 준비 시간 단축", "여러 사이트를 따로 열지 않고 순위, 가격표, 옵션 설명을 한 흐름에서 확인합니다."),
        ("가격표 확인 누락 감소", "공식 링크가 없는 차량은 '공식 PDF 확인 필요'로 분리해 확인 대상을 명확히 보여줍니다."),
        ("신차/가격 변경 이슈 빠른 공유", "신차, 가격표, 업무공지 알림을 상단 카드로 노출하고 운영 시 주기적 업데이트로 확장 가능합니다."),
        ("고객 상담 품질 표준화", "옵션 기능을 쉬운 설명과 상담 포인트로 나누어 신규 영업 담당자도 같은 기준으로 설명할 수 있습니다."),
        ("보안 리스크 최소화", "고객 개인정보 없이 공식/공개(public) 정보만 사용하는 영업 보조 대시보드입니다."),
    ]

    for title, body in effects:
        st.markdown(
            f"""
            <div class="effect-card">
                <div class="effect-title">{html_text(title)}</div>
                <div class="effect-body">{html_text(body)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="demo-note">
            현재 파일에 포함된 TOP50, 공식 링크, 옵션 요약, 알림 데이터를 보기 좋게 구성했습니다.
            외부 자동 수집은 운영 단계에서 주기적 업데이트 기능으로 확장할 수 있습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    if HEADER_IMAGE.exists():
        show_half_width_image(HEADER_IMAGE)
    else:
        st.markdown('<div class="main-title">🚗 영맨 헬퍼</div>', unsafe_allow_html=True)

    df = load_vehicles(file_version(VEHICLE_MASTER))
    options = load_options(file_version(OPTION_SUMMARY))
    mentions = load_mentions(file_version(OPTION_MENTIONS))
    newcars = load_newcar_roadmap()

    if df.empty:
        st.error("vehicle_master.csv 파일을 찾을 수 없거나 데이터가 비어 있습니다.")
        return

    show_newcar_premium_zone(newcars)
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["TOP50", "가격표", "옵션", "업무효과"])
    with tab1:
        show_rank_section(df)
    with tab2:
        show_pdf_section(df)
    with tab3:
        show_option_section(df, options, mentions)
    with tab4:
        show_effect_section()

    st.divider()
    show_summary_metrics(df)
    st.divider()
    st.caption("보안 원칙: 고객 개인정보, 실제 계약정보, 견적정보, 상담내역은 사용하지 않습니다. 공식/공개 자료 기반의 영업 보조 대시보드입니다.")


if __name__ == "__main__":
    main()
