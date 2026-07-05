# 영맨 헬퍼 Youngman Helper

렌터카 영업매니저가 모바일에서 국산/수입 통합 판매 TOP50 차량의 순위, 공식 가격표/PDF, 관심 옵션, 신차/가격표 이슈를 빠르게 확인하는 Streamlit 대시보드입니다.

## 현재 버전

- 화면명: 영맨 헬퍼
- 형태: 모바일 우선 Streamlit 웹 대시보드
- 주요 화면: TOP50 / 가격표 / 옵션
- 데이터: 최신 공개 판매실적 기준 국산/수입 통합 TOP50 및 공식 가격표 URL 기반
- 보안: 고객 개인정보, 계약정보, 실제 상담내역 미사용. 공개/공식 자료만 사용

## 포함 파일

```text
app.py                         # 모바일 우선 영맨 헬퍼 대시보드
vehicle_master.csv             # TOP50 차량/공식 PDF 링크/상태 데이터
data/option_summary.csv        # 차량별 옵션 설명
data/notifications.json        # 상단 알림 데이터
scripts/update_notifications.py # 뉴스 RSS 기반 알림 갱신
scripts/check_price_links.py    # 공식 PDF 파일 변경 여부 체크
docs/top50_url_review.csv       # TOP50 URL 검토표
docs/vehicle_image_backlog.md   # 차량 이미지 보강 체크리스트
requirements.txt
```

## 회사 PC에서 처음 실행하기

PowerShell에서 프로젝트 폴더로 이동합니다.

```powershell
cd "C:\Users\user\Downloads\youngman-helper-latest"
```

가상환경을 만들고 켭니다.

```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.venv\Scripts\Activate.ps1
```

필요 패키지를 설치합니다.

```powershell
pip install -r requirements.txt
```

앱을 실행합니다.

```powershell
streamlit run app.py
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:8501
```

## 운영/갱신 명령어

뉴스 알림 갱신:

```powershell
python scripts\update_notifications.py
```

공식 가격표/PDF 변경 체크:

```powershell
python scripts\check_price_links.py
```

판매순위 갱신:

```powershell
python scripts\update_sales_rankings.py --input data\sales_snapshot\monthly_sales.csv
```

앱 실행:

```powershell
streamlit run app.py
```

GitHub Actions 자동 갱신:

- `.github/workflows/refresh-dashboard-data.yml`
- 매일 공개 뉴스 알림과 공식 가격표 링크 상태를 갱신합니다.
- 필요하면 GitHub Actions 화면에서 수동 실행할 수 있습니다.

## 앞으로 채워야 할 데이터

`vehicle_master.csv`에서 다음 컬럼을 보강하면 화면에 바로 반영됩니다.

- `units_sold`: 판매/등록 대수
- `rank_change`: 전월 대비 순위 변동
- `image_url`: 차량 이미지 URL
- `price_url`: 공식 가격표 PDF 또는 가격 페이지
- `catalog_url`: 추가 PDF 링크. 현재는 카탈로그뿐 아니라 HEV 가격표 등 추가 PDF도 포함

판매순위 자동 갱신 스크립트는 월간 집계 CSV를 입력으로 사용합니다. 입력 파일은 최소 `brand`, `model` 컬럼이 필요하고, `rank`, `units_sold`, `vehicle`까지 있으면 더 안정적으로 갱신됩니다.
수입차 판매실적은 보통 다음 달 15일 전후 공개되므로, 현재 통합 TOP50은 국산 2026년 6월 판매실적과 수입 2026년 5월 등록실적을 최신 공개 기준으로 합산했습니다.

## 판매순위/링크 소스 메모

- 판매순위 원천: 다나와 자동차 공개 판매실적 월간 모델별 표 및 수입차 등록실적 공개표
- 공홈 확인 원천: 제조사 공식 홈페이지와 다운로드 센터
- 알림 갱신 원천: 공개 뉴스 RSS
- 가격표 검증 원천: 공식 PDF/모델 페이지

## 운영 소개

영맨 헬퍼는 국산/수입 통합 판매 TOP50 차량의 판매순위, 공식 가격표, 주요 옵션 설명, 신차/가격표 변경 이슈를 모바일에서 한 번에 확인하는 렌터카 영업지원 대시보드입니다. 영업매니저가 차량별 가격표와 옵션 설명, 신차 뉴스를 각각 검색하던 시간을 줄이고, 고객 상담 전 필요한 정보를 빠르게 확인하도록 돕습니다.
