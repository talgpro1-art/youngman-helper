from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_MASTER = ROOT / "vehicle_master.csv"
MONTHLY_SALES = ROOT / "data" / "sales_snapshot" / "monthly_sales.csv"

COLUMNS = [
    "rank", "rank_change", "brand", "model", "vehicle", "units_sold", "segment", "powertrain", "target_tag",
    "image_url", "price_url", "catalog_url", "active", "note", "image_file", "image_source_url",
    "image_review_status", "image_source_type",
]

RANKING = [
    ("현대", "더 뉴 그랜저", 10062, "국산 2026-06"),
    ("테슬라", "Model Y", 9188, "수입 2026-06"),
    ("기아", "쏘렌토", 8561, "국산 2026-06"),
    ("기아", "셀토스", 6685, "국산 2026-06"),
    ("기아", "카니발", 6267, "국산 2026-06"),
    ("기아", "스포티지", 6176, "국산 2026-06"),
    ("현대", "쏘나타 디 엣지", 5102, "국산 2026-06"),
    ("현대", "디 올 뉴 팰리세이드", 4211, "국산 2026-06"),
    ("현대", "아반떼", 4201, "국산 2026-06"),
    ("현대", "싼타페", 4068, "국산 2026-06"),
    ("현대", "투싼", 3285, "국산 2026-06"),
    ("현대", "포터2", 3270, "국산 2026-06"),
    ("기아", "EV5", 3192, "국산 2026-06"),
    ("기아", "K5", 3150, "국산 2026-06"),
    ("기아", "레이", 2954, "국산 2026-06"),
    ("기아", "EV3", 2838, "국산 2026-06"),
    ("BYD", "Dolphin", 2828, "수입 2026-06"),
    ("제네시스", "G80", 2757, "국산 2026-06"),
    ("현대", "더 뉴 스타리아", 2579, "국산 2026-06"),
    ("현대", "코나", 2558, "국산 2026-06"),
    ("기아", "PV5", 2349, "국산 2026-06"),
    ("제네시스", "GV70", 2294, "국산 2026-06"),
    ("BMW", "5 Series", 2266, "수입 2026-06"),
    ("벤츠", "E-Class", 2114, "수입 2026-06"),
    ("기아", "K8", 1981, "국산 2026-06"),
    ("기아", "모닝", 1919, "국산 2026-06"),
    ("기아", "니로", 1880, "국산 2026-06"),
    ("제네시스", "GV80", 1840, "국산 2026-06"),
    ("현대", "아이오닉 5", 1693, "국산 2026-06"),
    ("기아", "봉고 3", 1494, "국산 2026-06"),
    ("현대", "버스/트럭", 1452, "국산 2026-06"),
    ("기아", "버스/특수", 1389, "국산 2026-06"),
    ("KGM", "무쏘", 1333, "국산 2026-06"),
    ("르노", "필랑트", 1324, "국산 2026-06"),
    ("현대", "아이오닉 9", 1318, "국산 2026-06"),
    ("르노", "그랑 콜레오스", 1313, "국산 2026-06"),
    ("벤츠", "GLC-Class", 1221, "수입 2026-06"),
    ("기아", "레이 EV", 1205, "국산 2026-06"),
    ("현대", "베뉴", 1123, "국산 2026-06"),
    ("BYD", "SEALION 7", 1117, "수입 2026-06"),
    ("테슬라", "Model X", 1027, "수입 2026-06"),
    ("기아", "EV4", 1019, "국산 2026-06"),
    ("쉐보레", "트랙스 크로스오버", 842, "국산 2026-06"),
    ("기아", "EV6", 820, "국산 2026-06"),
    ("현대", "캐스퍼 일렉트릭", 774, "국산 2026-06"),
    ("현대", "더 뉴 아이오닉 6", 773, "국산 2026-06"),
    ("르노", "아르카나", 763, "국산 2026-06"),
    ("현대", "캐스퍼", 711, "국산 2026-06"),
    ("토요타", "All New RAV4", 674, "수입 2026-06"),
    ("벤츠", "GLE-Class", 634, "수입 2026-06"),
]


def normalize(value: object) -> str:
    return "".join(str(value or "").strip().lower().split())


def row_key(brand: object, model: object) -> tuple[str, str]:
    return normalize(brand), normalize(model)


def clean_unknown(value: object) -> str:
    text = str(value or "").strip()
    return "" if text in {"확인 필요", "업데이트 필요", "확인중", "nan", "NaN"} else text


def rank_change(old_rank: int | None, new_rank: int) -> str:
    if old_rank is None:
        return "NEW"
    diff = old_rank - new_rank
    if diff == 0:
        return "-"
    return f"▲{diff}" if diff > 0 else f"▼{abs(diff)}"


def default_segment(model: str) -> str:
    if any(token in model for token in ["Model Y", "Model X", "X3", "SEALION", "RAV4", "GLC", "GLE", "GV", "팰리세이드", "싼타페", "투싼", "코나", "콜레오스", "아르카나", "토레스"]):
        return "SUV"
    if any(token in model for token in ["Model 3", "5 Series", "E-Class", "A6", "그랜저", "쏘나타", "아반떼", "K5", "K8", "G80"]):
        return "세단"
    if any(token in model for token in ["Dolphin", "레이", "모닝", "베뉴", "캐스퍼"]):
        return "경차/소형"
    if any(token in model for token in ["카니발", "스타리아"]):
        return "MPV"
    if any(token in model for token in ["포터", "봉고", "PV5", "무쏘", "버스"]):
        return "상용/업무용"
    return "기타"


def infer_powertrain(model: str, current: object) -> str:
    current_text = clean_unknown(current)
    if current_text:
        return current_text
    if any(token in model for token in ["EV", "Model", "Dolphin", "SEALION", "아이오닉", "일렉트릭"]):
        return "전기"
    if "넥쏘" in model:
        return "수소전기"
    if any(token in model for token in ["필랑트", "그랑 콜레오스", "니로"]):
        return "하이브리드"
    return ""


def default_target(segment: str, powertrain: str) -> str:
    if "전기" in powertrain:
        return "전기차/법인/출퇴근/친환경"
    if segment == "SUV":
        return "패밀리/장기렌트/레저"
    if segment == "세단":
        return "개인/법인/출퇴근"
    if segment == "경차/소형":
        return "가성비/단기렌트/대차/도심형"
    if segment in {"상용", "상용/업무용"}:
        return "법인/소상공인/물류/업무용"
    if segment == "MPV":
        return "패밀리/법인/의전/다인승"
    return "영업 참고"


IMPORT_META = {
    row_key("테슬라", "Model Y"): {
        "segment": "전기차", "powertrain": "전기", "target_tag": "전기차/법인/출퇴근/친환경",
        "image_url": "https://digitalassets.tesla.com/tesla-contents/image/upload/f_auto%2Cq_auto/Model-Y-2-Specs-LR-AWD-Desktop-KR.png",
        "price_url": "https://www.tesla.com/ko_kr/modely/design", "catalog_url": "",
        "note": "공식 홈페이지 가격/주문 페이지", "image_source_url": "https://www.tesla.com/ko_kr/modely",
        "image_review_status": "approved", "image_source_type": "official_site",
    },
    row_key("테슬라", "Model 3"): {
        "segment": "전기차", "powertrain": "전기", "target_tag": "전기차/법인/출퇴근/친환경",
        "image_url": "https://digitalassets.tesla.com/tesla-contents/image/upload/f_auto%2Cq_auto/Model-3-Specs-RWD-Desktop-KR.png",
        "price_url": "https://www.tesla.com/ko_kr/model3/design", "catalog_url": "",
        "note": "공식 홈페이지 가격/주문 페이지", "image_source_url": "https://www.tesla.com/ko_kr/model3",
        "image_review_status": "approved", "image_source_type": "official_site",
    },
    row_key("BMW", "5 Series"): {
        "segment": "세단", "powertrain": "", "target_tag": "개인/법인/출퇴근",
        "image_url": "https://bmw.scene7.com/is/image/BMW/g60_ice_driving-dynamics_dsk_fb_en?fmt=webp&qlt=80&wid=1024",
        "price_url": "https://www.bmw.co.kr/ko/all-models/5-series/sedan/bmw-5-series-sedan-overview.html", "catalog_url": "",
        "note": "BMW 코리아 공식 모델/가격 확인 페이지", "image_source_url": "https://www.bmw.co.kr/ko/all-models/5-series/sedan/bmw-5-series-sedan-overview.html",
        "image_review_status": "approved", "image_source_type": "official_site",
    },
    row_key("BMW", "X3"): {
        "segment": "SUV", "powertrain": "", "target_tag": "패밀리/장기렌트/레저",
        "image_url": "https://bmw.scene7.com/is/image/BMW/g45_ice_intro-1%3A16to7?fit=constrain%2C1&fmt=webp&wid=2560",
        "price_url": "https://www.bmw.co.kr/ko/all-models/x-series/x3/bmw-x3.html", "catalog_url": "",
        "note": "BMW 코리아 공식 모델/가격 확인 페이지", "image_source_url": "https://www.bmw.co.kr/ko/all-models/x-series/x3/bmw-x3.html",
        "image_review_status": "approved", "image_source_type": "official_site",
    },
    row_key("벤츠", "E-Class"): {
        "segment": "세단", "powertrain": "", "target_tag": "개인/법인/출퇴근",
        "image_url": "https://media.oneweb.mercedes-benz.com/images/dynamic/asia/KR/214050/806/iris.png?BKGND=9&IMGT=P27&POV=BE030%2CPZM&uni=m",
        "price_url": "https://www.mercedes-benz.co.kr/passengercars/models/saloon/e-class/overview.html", "catalog_url": "",
        "note": "공식 홈페이지 모델/가격 확인 페이지", "image_source_url": "https://www.mercedes-benz.co.kr/passengercars/models/saloon/e-class/overview.html",
        "image_review_status": "approved", "image_source_type": "official_site",
    },
    row_key("BYD", "SEALION 7"): {
        "segment": "전기차", "powertrain": "전기", "target_tag": "전기차/법인/출퇴근/친환경",
        "image_url": "https://www.bydauto.kr/static/images/model/byd_sealion7/spac_img1_2.png",
        "price_url": "https://www.bydauto.kr/purchase/build-my-car/sealion7", "catalog_url": "https://www.bydauto.kr/static/file/BYD_SEALION_7_Catalog.pdf",
        "note": "공식 홈페이지 구매/견적 및 카탈로그 페이지", "image_source_url": "https://www.bydauto.kr/car/byd-sealion7",
        "image_review_status": "approved", "image_source_type": "official_site",
    },
    row_key("BYD", "Dolphin"): {
        "segment": "경차/소형", "powertrain": "전기", "target_tag": "전기차/출퇴근/도심형/가성비",
        "image_url": "", "price_url": "https://www.bydauto.kr/purchase/build-my-car/dolphin",
        "catalog_url": "https://www.bydauto.kr/static/file/BYD_DOLPHIN_Catalog.pdf",
        "note": "BYD 코리아 공식 모델/견적 페이지", "image_source_url": "https://www.bydauto.kr/car/byd-dolphin",
        "image_review_status": "", "image_source_type": "official_site",
    },
    row_key("테슬라", "Model X"): {
        "segment": "SUV", "powertrain": "전기", "target_tag": "전기차/법인/패밀리/프리미엄",
        "image_url": "", "price_url": "https://www.tesla.com/ko_KR/modelx/design/", "catalog_url": "",
        "note": "Tesla 코리아 공식 재고/주문 확인 페이지", "image_source_url": "https://www.tesla.com/ko_KR/support/meet-your-tesla/model-x",
        "image_review_status": "", "image_source_type": "official_site",
    },
    row_key("토요타", "All New RAV4"): {
        "segment": "SUV", "powertrain": "하이브리드", "target_tag": "패밀리/장기렌트/하이브리드/레저",
        "image_url": "", "price_url": "https://www.toyota.co.kr/build-my-car/build/?model=rav4", "catalog_url": "https://www.toyota.co.kr/assets/download/RAV4_HEV_spec.pdf",
        "note": "한국토요타 공식 모델/견적 페이지", "image_source_url": "https://www.toyota.co.kr/models/rav4hev/",
        "image_review_status": "", "image_source_type": "official_site",
    },
    row_key("벤츠", "GLC-Class"): {
        "segment": "SUV", "powertrain": "", "target_tag": "패밀리/법인/프리미엄/레저",
        "image_url": "", "price_url": "https://www.mercedes-benz.co.kr/passengercars/models/suv/glc/overview.html", "catalog_url": "",
        "note": "메르세데스-벤츠 코리아 공식 모델/가격 페이지", "image_source_url": "https://www.mercedes-benz.co.kr/passengercars/models/suv/glc/overview.html",
        "image_review_status": "", "image_source_type": "official_site",
    },
    row_key("벤츠", "GLE-Class"): {
        "segment": "SUV", "powertrain": "", "target_tag": "패밀리/법인/프리미엄/레저",
        "image_url": "", "price_url": "https://www.mercedes-benz.co.kr/passengercars/models/suv/gle/overview.html", "catalog_url": "",
        "note": "메르세데스-벤츠 코리아 공식 모델/가격 페이지", "image_source_url": "https://www.mercedes-benz.co.kr/passengercars/models/suv/gle/overview.html",
        "image_review_status": "", "image_source_type": "official_site",
    },
    row_key("아우디", "The new A6"): {
        "segment": "세단", "powertrain": "", "target_tag": "개인/법인/출퇴근",
        "image_url": "", "price_url": "https://www.audi.co.kr/kr/web/ko/models.html", "catalog_url": "",
        "note": "아우디 코리아 공식 모델/가격 확인 페이지", "image_source_url": "https://www.audi.co.kr/kr/web/ko/models.html",
        "image_review_status": "", "image_source_type": "official_site",
    },
}

RENAULT_LINKS = {
    row_key("르노", "필랑트"): (
        "https://cdn.renault.co.kr/upload/asset/price/price_filante_202607.pdf",
        "https://cdn.renault.co.kr/upload/asset/ebrochure/eBrochure_filante_202607.pdf",
        "필랑트 전용 공식 가격표(CDN 직접 PDF)",
    ),
    row_key("르노", "그랑 콜레오스"): (
        "https://cdn.renault.co.kr/upload/asset/price/price_koleos_202601.pdf",
        "",
        "그랑 콜레오스 전용 공식 가격표(CDN 직접 PDF)",
    ),
    row_key("르노", "아르카나"): (
        "https://cdn.renault.co.kr/upload/asset/price/price_Arkana_202607.pdf",
        "https://cdn.renault.co.kr/upload/asset/ebrochure/eBrochure_Arkana_202607.pdf",
        "아르카나 전용 공식 가격표(CDN 직접 PDF)",
    ),
}


def load_master() -> pd.DataFrame:
    df = pd.read_csv(VEHICLE_MASTER, dtype=str, encoding="utf-8-sig").fillna("")
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def main() -> None:
    master = load_master()
    lookup = {row_key(row["brand"], row["model"]): row.to_dict() for _, row in master.iterrows()}
    old_rank = {}
    for _, row in master.iterrows():
        try:
            old_rank[row_key(row["brand"], row["model"])] = int(float(row["rank"]))
        except (TypeError, ValueError):
            pass

    rows = []
    sales_rows = []
    for new_rank, (brand, model, units_sold, source_period) in enumerate(RANKING, start=1):
        key = row_key(brand, model)
        row = {col: "" for col in COLUMNS}
        row.update({col: lookup.get(key, {}).get(col, "") for col in COLUMNS})
        row.update(IMPORT_META.get(key, {}))

        row["rank"] = new_rank
        row["rank_change"] = rank_change(old_rank.get(key), new_rank)
        row["brand"] = brand
        row["model"] = model
        row["vehicle"] = f"{brand} {model}"
        row["units_sold"] = f"{units_sold:,}"
        row["segment"] = clean_unknown(row.get("segment")) or default_segment(model)
        row["powertrain"] = infer_powertrain(model, row.get("powertrain"))
        row["target_tag"] = clean_unknown(row.get("target_tag")) or default_target(row["segment"], row["powertrain"])
        row["active"] = "Y"
        row["image_review_status"] = clean_unknown(row.get("image_review_status"))
        row["image_source_type"] = clean_unknown(row.get("image_source_type"))

        if key in RENAULT_LINKS:
            price_url, catalog_url, note = RENAULT_LINKS[key]
            row["price_url"] = price_url
            row["catalog_url"] = catalog_url
            row["note"] = note

        rows.append({col: row.get(col, "") for col in COLUMNS})
        sales_rows.append({
            "rank": new_rank,
            "brand": brand,
            "model": model,
            "units_sold": units_sold,
            "source_period": source_period,
        })

    pd.DataFrame(rows, columns=COLUMNS).to_csv(VEHICLE_MASTER, index=False, encoding="utf-8-sig")
    MONTHLY_SALES.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sales_rows).to_csv(MONTHLY_SALES, index=False, encoding="utf-8-sig")
    print(f"Updated {VEHICLE_MASTER.name}: {len(rows)} rows")
    print(f"Updated {MONTHLY_SALES.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
