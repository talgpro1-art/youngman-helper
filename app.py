from __future__ import annotations

import base64
import json
import mimetypes
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
NOTIFICATIONS = ROOT / "data" / "notifications.json"
NEWCAR_ROADMAP = ROOT / "data" / "newcar_roadmap.csv"
NEWCAR_ROADMAP_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTTCzFCPz6nPFnu-oRoTjB16Ng7hhPAy811JU3DZcnSKglptFHHf3hLOVIXN4Y-yis7_RZhK52_Ys1m/pub?gid=1952505960&single=true&output=csv"
CAR_IMAGE_DIR = ROOT / "assets" / "cars"
HEADER_IMAGE = ROOT / "assets" / "header.png"
APP_ICON = ROOT / "assets" / "icon.png"
APPROVED_IMAGE_SOURCE_TYPES = {"official_newsroom", "official_site", "official_press_release", "manual"}

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
    button[data-testid="collapsedControl"] {display:none!important;}
    .block-container{padding-top:3.2rem;padding-left:1rem;padding-right:1rem;max-width:980px;}
    .mobile-section-title{font-size:1.15rem;font-weight:850;margin:1.1rem 0 .55rem 0;}
    .notice-zone{border:1px solid #e5e7eb;border-radius:14px;background:#fff;padding:.82rem;margin:.75rem 0 .85rem 0;box-shadow:0 2px 10px rgba(15,23,42,.05);}
    .notice-head{display:flex;justify-content:space-between;gap:.65rem;align-items:center;margin-bottom:.45rem;}
    .notice-title{font-size:1rem;font-weight:950;color:#111827;}
    .notice-count{border-radius:999px;background:#f3f4f6;color:#374151;padding:.18rem .5rem;font-size:.72rem;font-weight:850;white-space:nowrap;}
    .notice-card{border-radius:12px;padding:.68rem .72rem;margin-top:.48rem;border:1px solid #dbeafe;background:#eff6ff;}
    .notice-card.warning{border-color:#fde68a;background:#fffbeb;}
    .notice-card.critical{border-color:#fecaca;background:#fef2f2;}
    .notice-card.info{border-color:#dbeafe;background:#eff6ff;}
    .notice-card-title{font-size:.92rem;font-weight:900;color:#111827;line-height:1.35;}
    .notice-body{font-size:.84rem;color:#4b5563;line-height:1.45;margin-top:.25rem;}
    .notice-meta{font-size:.74rem;color:#6b7280;line-height:1.35;margin-top:.35rem;}
    .notice-link{display:inline-flex;margin-top:.45rem;color:#1d4ed8!important;font-size:.8rem;font-weight:850;text-decoration:none!important;}
    .premium-zone{border:1px solid #bae6fd;border-radius:16px;background:linear-gradient(180deg,#f0f9ff 0%,#fff 100%);padding:1rem;margin:.9rem 0 .85rem 0;box-shadow:0 6px 18px rgba(14,116,144,.10);}
    .premium-head{display:flex;justify-content:space-between;gap:.7rem;align-items:flex-start;margin-bottom:.75rem;}
    .premium-title{font-size:1.1rem;font-weight:950;color:#0f172a;line-height:1.3;}
    .premium-sub{color:#475569;font-size:.84rem;line-height:1.45;margin-top:.2rem;}
    .premium-badge{display:inline-flex;align-items:center;white-space:nowrap;border-radius:999px;background:#0f172a;color:#fff;padding:.25rem .6rem;font-size:.72rem;font-weight:850;}
    .roadmap-card{border:1px solid #e0f2fe;border-radius:14px;background:#fff;padding:.85rem;margin-top:.55rem;}
    .roadmap-topline{display:flex;justify-content:space-between;gap:.7rem;align-items:flex-start;}
    .roadmap-car{font-size:1rem;font-weight:900;color:#111827;line-height:1.3;}
    .roadmap-dday{border-radius:999px;background:#ecfeff;color:#0e7490;padding:.18rem .48rem;font-size:.74rem;font-weight:900;white-space:nowrap;}
    .roadmap-summary{color:#475569;font-size:.84rem;line-height:1.45;margin-top:.35rem;}
    .roadmap-section-label{font-size:.82rem;font-weight:900;color:#075985;margin:.7rem 0 .3rem 0;}
    .vehicle-card{border:1px solid #e5e7eb;border-radius:14px;padding:.78rem;margin-bottom:.75rem;background:#fff;box-shadow:0 2px 8px rgba(15,23,42,.05);}
    .vehicle-card-head{display:flex;justify-content:space-between;gap:.75rem;align-items:flex-start;}
    .rank-badge{font-size:1.45rem;font-weight:900;color:#111827;letter-spacing:-.04em;white-space:nowrap;}
    .rank-change{font-size:.85rem;font-weight:700;color:#4b5563;margin-left:.25rem;}
    .status-badge{display:inline-flex;align-items:center;border-radius:999px;background:#fef3c7;color:#92400e;padding:.16rem .48rem;font-size:.72rem;font-weight:850;margin-left:.35rem;vertical-align:middle;white-space:nowrap;}
    .vehicle-name{font-size:1.18rem;font-weight:900;color:#111827;text-align:right;letter-spacing:-.04em;}
    .vehicle-meta{color:#6b7280;font-size:.86rem;text-align:right;margin-top:.1rem;line-height:1.35;}
    .vehicle-main{display:grid;grid-template-columns:136px minmax(0,1fr);gap:.72rem;align-items:start;margin-top:.72rem;}
    .vehicle-thumb{display:block;width:136px;height:88px;border-radius:11px;object-fit:cover;background:#f3f4f6;}
    .car-placeholder{width:136px;height:88px;border-radius:11px;background:linear-gradient(135deg,#f3f4f6,#e5e7eb);display:flex;align-items:center;justify-content:center;font-size:1.7rem;}
    .tag-row{display:flex;flex-wrap:wrap;gap:.35rem;margin:0 0 .45rem 0;}
    .pill{display:inline-block;border-radius:999px;background:#f3f4f6;color:#374151;padding:.22rem .55rem;font-size:.76rem;font-weight:700;}
    .vehicle-actions{display:flex;flex-wrap:wrap;gap:.38rem;}
    .compact-link{display:inline-flex;align-items:center;justify-content:center;min-height:32px;padding:.4rem .64rem;border-radius:10px;background:#111827;color:#fff!important;text-decoration:none!important;font-size:.78rem;font-weight:850;line-height:1.15;white-space:nowrap;}
    .compact-link.secondary{background:#374151;}
    .compact-link.disabled{background:#e5e7eb;color:#6b7280!important;pointer-events:none;}
    .pdf-button{display:block;width:100%;text-align:center;padding:.78rem .72rem;border-radius:12px;margin-top:.45rem;background:#111827;color:#fff!important;text-decoration:none!important;font-weight:800;font-size:.92rem;}
    .pdf-button.secondary{background:#374151;}
    .pdf-button.disabled{background:#e5e7eb;color:#6b7280!important;pointer-events:none;font-weight:850;}
    .card-note{color:#9ca3af;font-size:.76rem;line-height:1.35;margin-top:.42rem;}
    .option-card,.effect-card{border:1px solid #e5e7eb;border-radius:14px;padding:.95rem;margin-bottom:.65rem;background:#fff;box-shadow:0 2px 8px rgba(15,23,42,.04);}
    .option-name,.effect-title{font-size:1rem;font-weight:900;margin-bottom:.35rem;color:#111827;}
    .option-label{display:inline-block;font-size:.74rem;font-weight:850;color:#4b5563;background:#f3f4f6;border-radius:999px;padding:.15rem .48rem;margin:.45rem 0 .25rem 0;}
    .effect-body{color:#4b5563;font-size:.9rem;line-height:1.5;}
    .effect-list{margin:.35rem 0 0 1rem;padding:0;color:#374151;line-height:1.55;font-size:.9rem;}
    .talking-point{border-left:4px solid #2563eb;background:#eff6ff;padding:.65rem .72rem;border-radius:10px;margin-top:.5rem;color:#1e3a8a;line-height:1.45;font-size:.9rem;}
    .small-muted{font-size:.82rem;color:#6b7280;line-height:1.4;}
    .demo-note{border:1px solid #dbeafe;background:#eff6ff;border-radius:14px;padding:.9rem;color:#1e3a8a;font-size:.9rem;line-height:1.5;margin-top:.75rem;}
    div[data-testid="stMetric"]{background:#f9fafb;border:1px solid #e5e7eb;border-radius:14px;padding:.65rem;}
    @media(max-width:768px){
        .block-container{padding-top:3.4rem;padding-left:.75rem;padding-right:.75rem;}
        .vehicle-card{padding:.68rem;border-radius:13px;}
        .rank-badge{font-size:1.28rem;}
        .vehicle-name{font-size:1.05rem;}
        .vehicle-meta{font-size:.78rem;}
        .vehicle-main{grid-template-columns:96px minmax(0,1fr);gap:.58rem;margin-top:.58rem;}
        .vehicle-thumb,.car-placeholder{width:96px;height:66px;border-radius:9px;}
        .car-placeholder{font-size:1.35rem;}
        .pill{font-size:.7rem;padding:.18rem .45rem;}
        .tag-row{gap:.28rem;margin-bottom:.38rem;}
        .compact-link{min-height:30px;padding:.36rem .52rem;font-size:.74rem;}
        .pdf-button{padding:.76rem .65rem;font-size:.9rem;}
        .option-card,.effect-card{padding:.82rem;}
        .notice-zone{padding:.72rem;}
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


def file_version(path: Path) -> int:
    return path.stat().st_mtime_ns if path.exists() else 0


def display_units(value: object) -> str:
    text = safe_str(value)
    return "업데이트 예정" if not text or text == "업데이트 필요" else text


def display_rank_change(value: object) -> str:
    text = safe_str(value)
    return "-" if not text or text in {"-", "업데이트 필요"} else text


def is_pdf_url(url: str) -> bool:
    clean = safe_str(url).split("?", 1)[0].split("#", 1)[0].lower()
    return clean.endswith(".pdf")


def is_hybrid_price_url(url: str) -> bool:
    clean = safe_str(url).lower()
    return "hybrid" in clean or "hev" in clean


def price_button_label(url: str, has_hybrid_pair: bool = False) -> str:
    lower = safe_str(url).lower()
    if "genesis.com/kr/ko/support/download-center" in lower:
        return "공홈 가격표/카탈로그 보기"
    if not is_pdf_url(url):
        return "공홈 가격표 보기"
    if is_hybrid_price_url(url):
        return "공식 가격표(하이브리드)"
    if has_hybrid_pair:
        return "공식 가격표(일반)"
    return "공식 가격표"


def price_links(row: pd.Series) -> list[tuple[str, str, bool]]:
    urls = []
    for key in ["price_url", "catalog_url"]:
        url = safe_str(row.get(key))
        if url.startswith("http") and url not in urls:
            urls.append(url)
    has_hybrid_pair = any(is_hybrid_price_url(url) for url in urls) and len(urls) > 1
    return [(url, price_button_label(url, has_hybrid_pair), idx > 0) for idx, url in enumerate(urls)]


def consultation_sentence(vehicle_name: str, option_name: str, sales_point: str) -> str:
    if sales_point:
        return f"{vehicle_name} 상담에서는 '{option_name}'을 {sales_point} 관점으로 설명하면 좋습니다."
    return f"{vehicle_name} 상담에서는 '{option_name}'을 고객이 바로 체감할 수 있는 편의·안전 포인트로 설명하면 좋습니다."


def image_file_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def vehicle_image_source(row: pd.Series) -> str | Path | None:
    if safe_str(row.get("image_review_status")).lower() != "approved":
        return None
    if safe_str(row.get("image_source_type")).lower() not in APPROVED_IMAGE_SOURCE_TYPES:
        return None
    image_file = safe_str(row.get("image_file"))
    if image_file:
        for candidate in [ROOT / image_file, CAR_IMAGE_DIR / image_file, CAR_IMAGE_DIR / Path(image_file).name]:
            if candidate.exists() and candidate.is_file():
                return candidate
    image_url = safe_str(row.get("image_url"))
    return image_url if image_url.startswith("http") else None


def vehicle_thumb_html(source: str | Path | None, name: str) -> str:
    if isinstance(source, Path) and source.exists():
        src = image_file_to_data_url(source)
        return f'<img src="{src}" class="vehicle-thumb" alt="{html_text(name)}">'
    source_text = safe_str(source)
    if source_text.startswith("http"):
        return f'<img src="{escape(source_text)}" class="vehicle-thumb" alt="{html_text(name)}">'
    return '<div class="car-placeholder">🚗</div>'


def show_half_width_image(source: str | Path) -> None:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.image(source, width="stretch")


@st.cache_data(show_spinner=False)
def load_vehicles(version: int) -> pd.DataFrame:
    if not VEHICLE_MASTER.exists():
        return pd.DataFrame()
    df = pd.read_csv(VEHICLE_MASTER)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    defaults = {
        "rank": range(1, len(df) + 1), "rank_change": "-", "brand": "", "model": "", "vehicle": "",
        "units_sold": "업데이트 필요", "segment": "", "powertrain": "", "target_tag": "",
        "image_url": "", "image_file": "", "image_source_url": "", "image_source_type": "",
        "image_review_status": "", "price_url": "", "catalog_url": "", "active": "Y", "note": "",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = list(default) if col == "rank" else default
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(999).astype(int)
    df["vehicle_name"] = df.apply(lambda r: safe_str(r.get("vehicle")) or f"{safe_str(r.get('brand'))} {safe_str(r.get('model'))}".strip(), axis=1)
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


@st.cache_data(show_spinner=False)
def load_mentions(version: int) -> pd.DataFrame:
    if not OPTION_MENTIONS.exists():
        return pd.DataFrame()
    df = pd.read_csv(OPTION_MENTIONS)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    return df


@st.cache_data(show_spinner=False)
def load_notifications(version: int) -> list[dict]:
    if not NOTIFICATIONS.exists():
        return []
    try:
        data = json.loads(NOTIFICATIONS.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


@st.cache_data(show_spinner=False, ttl=600)
def load_newcar_roadmap() -> pd.DataFrame:
    try:
        df = pd.read_csv(NEWCAR_ROADMAP_URL) if NEWCAR_ROADMAP_URL else pd.read_csv(NEWCAR_ROADMAP)
    except Exception:
        if not NEWCAR_ROADMAP.exists():
            return pd.DataFrame()
        df = pd.read_csv(NEWCAR_ROADMAP)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    df["launch_dt"] = pd.to_datetime(df.get("launch_date"), errors="coerce")
    df["priority"] = pd.to_numeric(df.get("priority"), errors="coerce").fillna(99).astype(int)
    return df


def render_link_button(url: str, label: str, secondary: bool = False, disabled_label: str | None = None) -> None:
    url = safe_str(url)
    if url.startswith("http"):
        cls = "pdf-button secondary" if secondary else "pdf-button"
        st.markdown(f'<a href="{escape(url)}" target="_blank" class="{cls}">{html_text(label)}</a>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="pdf-button disabled">{html_text(disabled_label or f"{label} 없음")}</div>', unsafe_allow_html=True)


def dday_label(value: object) -> str:
    launch_dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(launch_dt):
        return "일정 확인"
    diff = (launch_dt.normalize() - pd.Timestamp.today().normalize()).days
    if diff > 0:
        return f"D-{diff}"
    if diff == 0:
        return "D-Day"
    return f"D+{abs(diff)}"


def confidence_label(value: object) -> str:
    return {"confirmed": "공식 확인", "likely": "출시 유력", "rumor": "검증 필요"}.get(safe_str(value).lower(), "확인중")


def price_status_label(value: object) -> str:
    return {"available": "가격표 있음", "pending": "가격표 대기", "none": "가격표 없음"}.get(safe_str(value).lower(), "가격표 확인중")


def notification_meta(item: dict) -> str:
    date = safe_str(item.get("article_date")) or safe_str(item.get("date")) or safe_str(item.get("created_at")) or safe_str(item.get("published"))
    vehicle = safe_str(item.get("vehicle"))
    if not vehicle:
        vehicle = f"{safe_str(item.get('brand'))} {safe_str(item.get('model'))}".strip()
    source = safe_str(item.get("source"))
    return " · ".join(part for part in [date, vehicle, source] if part)


def show_notifications(items: list[dict]) -> None:
    if not items:
        return
    cards = [f"""
    <div class="notice-zone">
      <div class="notice-head">
        <div class="notice-title">🔔 상단 알림</div>
        <div class="notice-count">{len(items[:5])}건</div>
      </div>
    """]
    for item in items[:5]:
        severity = safe_str(item.get("severity"), "info").lower()
        if severity not in {"info", "warning", "critical"}:
            severity = "info"
        title = html_text(item.get("title"), "알림")
        body = html_text(item.get("body"))
        meta = html_text(notification_meta(item))
        link = safe_str(item.get("link"))
        link_html = f'<a class="notice-link" href="{escape(link)}" target="_blank">자세히 보기</a>' if link.startswith("http") else ""
        body_html = f'<div class="notice-body">{body}</div>' if body else ""
        meta_html = f'<div class="notice-meta">{meta}</div>' if meta else ""
        cards.append(f"""
        <div class="notice-card {severity}">
          <div class="notice-card-title">{title}</div>
          {body_html}
          {meta_html}
          {link_html}
        </div>
        """)
    cards.append("</div>")
    st.markdown("\n".join(dedent(card).strip() for card in cards), unsafe_allow_html=True)


def filtered_newcars(newcars: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if newcars.empty:
        return pd.DataFrame(), pd.DataFrame()
    today = pd.Timestamp.today().normalize()
    statuses = newcars.get("status", pd.Series([""] * len(newcars))).astype(str).str.lower()
    launch_dt = newcars.get("launch_dt", pd.Series([pd.NaT] * len(newcars)))
    upcoming = newcars[(statuses == "upcoming") & (launch_dt.isna() | ((launch_dt >= today) & (launch_dt <= today + pd.Timedelta(days=60))))].copy()
    recent = newcars[(statuses == "recent") & (launch_dt.isna() | ((launch_dt >= today - pd.Timedelta(days=14)) & (launch_dt <= today)))].copy()
    return upcoming.sort_values(["priority", "launch_dt"]).head(5), recent.sort_values(["priority", "launch_dt"], ascending=[True, False]).head(5)


def show_newcar_premium_zone(newcars: pd.DataFrame) -> None:
    upcoming, recent = filtered_newcars(newcars)
    total = len(upcoming) + len(recent)
    parts = [f"""
    <div class="premium-zone"><div class="premium-head"><div>
    <div class="premium-title">🚨 신차 출시 로드맵</div>
    <div class="premium-sub">향후 60일 출시 예정 차량과 최근 2주 출시 차량의 가격표를 먼저 확인합니다.</div>
    </div><div class="premium-badge">{total}건</div></div>
    """]
    if total == 0:
        parts.append('<div class="roadmap-card"><div class="roadmap-car">업데이트 대기</div><div class="roadmap-summary">현재 D+60 출시 예정 또는 최근 2주 내 출시 차량 데이터가 없습니다.</div></div>')
    if not upcoming.empty:
        parts.append('<div class="roadmap-section-label">출시 예정 D+60</div>')
        for _, row in upcoming.iterrows():
            source_url = safe_str(row.get("source_url"))
            source_html = f'<div class="roadmap-summary"><a href="{escape(source_url)}" target="_blank">출처 확인</a></div>' if source_url.startswith("http") else ""
            launch_date = html_text(row.get("launch_date"))
            parts.append(f"""
            <div class="roadmap-card"><div class="roadmap-topline"><div>
            <div class="roadmap-car">{html_text(row.get('vehicle'), '신차')}</div>
            <div class="small-muted">{launch_date + ' 출시 예정' if launch_date else '출시 일정 확인중'}</div>
            </div><div class="roadmap-dday">{html_text(dday_label(row.get('launch_dt')))}</div></div>
            <div class="roadmap-summary">{html_text(row.get('summary'), '출시 일정 확인 필요')}</div>
            <div class="small-muted">출시 신뢰도: {html_text(confidence_label(row.get('launch_confidence')))} · 가격표: {html_text(price_status_label(row.get('price_status')))}</div>{source_html}</div>
            """)
    if not recent.empty:
        parts.append('<div class="roadmap-section-label">최근 출시 / 가격표</div>')
        for _, row in recent.iterrows():
            links_html = ""
            for url, label in [(safe_str(row.get("price_url")), "신차 가격표 바로보기"), (safe_str(row.get("catalog_url")), "신차 카탈로그 바로보기")]:
                if url.startswith("http"):
                    cls = "pdf-button secondary" if "카탈로그" in label else "pdf-button"
                    links_html += f'<a href="{escape(url)}" target="_blank" class="{cls}">{html_text(label)}</a>'
            launch_date = html_text(row.get("launch_date"))
            parts.append(f"""
            <div class="roadmap-card"><div class="roadmap-topline"><div>
            <div class="roadmap-car">{html_text(row.get('vehicle'), '신차')}</div>
            <div class="small-muted">{launch_date + ' 출시' if launch_date else '최근 출시/가격 공개'}</div>
            </div><div class="roadmap-dday">{html_text(dday_label(row.get('launch_dt')))}</div></div>
            <div class="roadmap-summary">{html_text(row.get('summary'), '최근 출시 차량입니다.')}</div>
            <div class="small-muted">출시 신뢰도: {html_text(confidence_label(row.get('launch_confidence')))} · 가격표: {html_text(price_status_label(row.get('price_status')))}</div>{links_html}</div>
            """)
    parts.append("</div>")
    st.markdown("\n".join(dedent(part).strip() for part in parts), unsafe_allow_html=True)


def filter_vehicles(df: pd.DataFrame) -> pd.DataFrame:
    search = st.text_input("차량명 검색", placeholder="예: 쏘렌토, 그랜저, 카니발")
    segments = ["전체"] + sorted([safe_str(v) for v in df.get("segment", pd.Series()).dropna().unique().tolist() if safe_str(v)])
    selected_segment = st.selectbox("차급 필터", segments, index=0)
    filtered = df.copy()
    if search.strip():
        filtered = filtered[filtered["vehicle_name"].str.lower().str.contains(search.strip().lower(), na=False)]
    if selected_segment != "전체":
        filtered = filtered[filtered["segment"].astype(str) == selected_segment]
    return filtered.reset_index(drop=True)


def show_vehicle_card(row: pd.Series) -> None:
    name = safe_str(row.get("vehicle_name"))
    rank = safe_str(row.get("rank"))
    rank_change = display_rank_change(row.get("rank_change"))
    units = display_units(row.get("units_sold"))
    segment = safe_str(row.get("segment"))
    tags = [tag for tag in [segment, safe_str(row.get("powertrain")), safe_str(row.get("target_tag"))] if tag]
    tag_html = "".join(f'<span class="pill">{html_text(tag)}</span>' for tag in tags)
    tag_html = f'<div class="tag-row">{tag_html}</div>' if tag_html else ""
    links = price_links(row)
    if links:
        link_html = "".join(f'<a href="{escape(url)}" target="_blank" class="{"compact-link secondary" if secondary else "compact-link"}">{html_text(label)}</a>' for url, label, secondary in links)
    else:
        link_html = '<span class="compact-link disabled">공식 PDF 확인 필요</span>'
    note = safe_str(row.get("note"))
    note_html = f'<div class="card-note">비고: {html_text(note)}</div>' if note else ""
    status_html = '<span class="status-badge">확인 필요</span>' if safe_str(row.get("active"), "Y").upper() == "N" else ""
    thumb_html = vehicle_thumb_html(vehicle_image_source(row), name)
    meta = f"{units} · {segment or '차급 업데이트 예정'}"
    st.markdown(f"""
    <div class="vehicle-card">
      <div class="vehicle-card-head"><div><span class="rank-badge">{html_text(rank)}위</span><span class="rank-change">{html_text(rank_change)}</span></div>
      <div><div class="vehicle-name">{html_text(name)}{status_html}</div><div class="vehicle-meta">{html_text(meta)}</div></div></div>
      <div class="vehicle-main"><div>{thumb_html}</div><div>{tag_html}<div class="vehicle-actions">{link_html}</div>{note_html}</div></div>
    </div>
    """, unsafe_allow_html=True)


def rank_table(df: pd.DataFrame) -> pd.DataFrame:
    table = df[["rank", "rank_change", "vehicle_name", "units_sold", "segment", "has_pdf", "active"]].copy()
    table["rank_change"] = table["rank_change"].apply(display_rank_change)
    table["units_sold"] = table["units_sold"].apply(display_units)
    table["has_pdf"] = table["has_pdf"].map(lambda ready: "있음" if ready else "확인 필요")
    table["active"] = table["active"].astype(str).str.upper().map(lambda value: "확인 필요" if value == "N" else "활성")
    table.columns = ["순위", "변동", "차량", "판매/등록대수", "차급", "공식링크", "상태"]
    return table


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
        filtered = filtered[filtered["vehicle_name"].str.lower().str.contains(keyword.strip().lower(), na=False)]
    for _, row in filtered.iterrows():
        with st.expander(f"{int(row['rank'])}위 · {row['vehicle_name']}"):
            st.write(f"**차급:** {safe_str(row.get('segment')) or '-'}  /  **영업 태그:** {safe_str(row.get('target_tag')) or '-'}")
            links = price_links(row)
            if links:
                for url, label, secondary in links:
                    render_link_button(url, label, secondary=secondary)
            else:
                render_link_button("", "공식 가격표 보기", disabled_label="공식 PDF 확인 필요")
            if safe_str(row.get("note")):
                st.caption(f"비고: {safe_str(row.get('note'))}")


def show_option_section(df: pd.DataFrame, options: pd.DataFrame, mentions: pd.DataFrame) -> None:
    st.markdown('<div class="mobile-section-title">⭐ 차량별 관심 옵션·기능 설명</div>', unsafe_allow_html=True)
    st.caption("TOP10 차량 중심으로 상담 문장을 먼저 보여줍니다. 운영 시 공식 가격표와 안내 문구를 주기적으로 업데이트할 수 있습니다.")
    top10 = df[df["rank"] <= 10].copy()
    scope = st.radio("옵션 표시 범위", ["TOP10 데모", "전체 차량"], horizontal=True)
    choices = (top10 if scope == "TOP10 데모" and not top10.empty else df)["vehicle_name"].tolist()
    selected = st.selectbox("차량 선택", choices)
    row = df[df["vehicle_name"] == selected].iloc[0]
    brand, model, vehicle_name = safe_str(row.get("brand")), safe_str(row.get("model")), safe_str(row.get("vehicle_name"))
    matched = options[(options["brand"].astype(str) == brand) & (options["model"].astype(str) == model)] if not options.empty else pd.DataFrame()
    if matched.empty:
        st.info("아직 옵션 설명 데이터가 없습니다.")
        return
    matched_mentions = mentions[(mentions["brand"].astype(str) == brand) & (mentions["model"].astype(str) == model)] if not mentions.empty else pd.DataFrame()
    for _, opt in matched.iterrows():
        option_name = safe_str(opt.get("option_name"), "관심 옵션")
        function = safe_str(opt.get("function"), "차량 이용 편의성과 안전성을 높이는 기능")
        sales_point = safe_str(opt.get("sales_point"))
        mention_html = '<div class="small-muted">온라인 언급률 데이터는 아직 준비되지 않았습니다.</div>'
        if not matched_mentions.empty:
            mention_rows = matched_mentions[matched_mentions["option_name"].astype(str) == option_name]
            if not mention_rows.empty:
                mention = mention_rows.iloc[0]
                keywords = safe_str(mention.get("keywords")).replace(";", " · ")
                mention_html = f'<div style="border-radius:12px;background:#eef2ff;border:1px solid #c7d2fe;padding:.65rem .75rem;margin:.55rem 0;"><div style="font-size:1.02rem;font-weight:900;color:#3730a3;">온라인 언급률 {html_text(mention.get("mention_rate"), "0")}%</div><div style="font-size:.82rem;color:#4338ca;">언급 수 {html_text(mention.get("mention_count"), "0")}/{html_text(mention.get("total_mentions"), "0")}</div><div style="font-size:.82rem;color:#4338ca;">주요 키워드: {html_text(keywords)}</div></div>'
        status_html = f'<div class="small-muted">{html_text(opt.get("data_status"))}</div>' if safe_str(opt.get("data_status")) else ""
        st.markdown(f'<div class="option-card"><div class="option-name">⭐ {html_text(option_name)}</div>{mention_html}<div class="option-label">쉬운 설명</div><div class="effect-body">{html_text(function)}</div><div class="option-label">고객에게 이렇게 설명</div><div class="talking-point">{html_text(consultation_sentence(vehicle_name, option_name, sales_point))}</div>{status_html}</div>', unsafe_allow_html=True)
    st.info("옵션명·설명은 영업 상담 보조용 요약입니다. 실제 적용 트림, 옵션 구성, 가격은 반드시 공식 가격표를 확인하세요.")


def show_effect_section() -> None:
    st.markdown('<div class="mobile-section-title">📌 업무효과</div>', unsafe_allow_html=True)
    st.caption("영맨 헬퍼는 공개 자료 기반 정보를 한 화면에 모아 상담 준비 과정을 표준화합니다.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="effect-card"><div class="effect-title">기존 업무 방식</div><ul class="effect-list"><li>차량 판매순위 확인</li><li>브랜드별 가격표 검색</li><li>옵션 설명 별도 확인</li><li>신차/가격 변경 이슈 개별 확인</li></ul></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="effect-card"><div class="effect-title">영맨 헬퍼 적용 후</div><ul class="effect-list"><li>TOP50 순위와 공식 가격표를 한 화면에서 확인</li><li>차량별 옵션 설명을 상담 문장으로 확인</li><li>신차 출시·가격표 이슈를 상단에서 빠르게 확인</li><li>공식/공개 자료 기반으로 보안 부담 최소화</li></ul></div>', unsafe_allow_html=True)
    for title, body in [
        ("영업 준비 시간 단축", "여러 사이트를 따로 열지 않고 순위, 가격표, 옵션 설명을 한 흐름에서 확인합니다."),
        ("가격표 확인 누락 감소", "공식 링크가 없는 차량은 '공식 PDF 확인 필요'로 분리해 확인 대상을 명확히 보여줍니다."),
        ("신차/가격 변경 이슈 빠른 공유", "신차, 가격표, 업무공지 알림을 상단 카드로 노출하고 운영 시 주기적 업데이트로 확장 가능합니다."),
        ("고객 상담 품질 표준화", "옵션 기능을 쉬운 설명과 상담 포인트로 나누어 신규 영업 담당자도 같은 기준으로 설명할 수 있습니다."),
        ("보안 리스크 최소화", "고객 개인정보 없이 공식/공개(public) 정보만 사용하는 영업 보조 대시보드입니다."),
    ]:
        st.markdown(f'<div class="effect-card"><div class="effect-title">{html_text(title)}</div><div class="effect-body">{html_text(body)}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="demo-note">외부 자동 수집은 운영 단계에서 주기적 업데이트 기능으로 확장할 수 있습니다.</div>', unsafe_allow_html=True)


def show_summary_metrics(df: pd.DataFrame) -> None:
    st.markdown('<div class="mobile-section-title">운영 데이터 요약</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("관리 차종", f"{len(df)}개")
    m2.metric("공식링크", f"{int(df['has_pdf'].sum()) if not df.empty else 0}개")
    m3.metric("활성", f"{int((df['active'].astype(str).str.upper() == 'Y').sum()) if not df.empty else 0}개")


def main() -> None:
    if HEADER_IMAGE.exists():
        show_half_width_image(HEADER_IMAGE)
    else:
        st.markdown('<div style="font-size:2rem;font-weight:900;">🚗 영맨 헬퍼</div>', unsafe_allow_html=True)
    df = load_vehicles(file_version(VEHICLE_MASTER))
    options = load_options(file_version(OPTION_SUMMARY))
    mentions = load_mentions(file_version(OPTION_MENTIONS))
    notifications = load_notifications(file_version(NOTIFICATIONS))
    newcars = load_newcar_roadmap()
    if df.empty:
        st.error("vehicle_master.csv 파일을 찾을 수 없거나 데이터가 비어 있습니다.")
        return
    show_notifications(notifications)
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
