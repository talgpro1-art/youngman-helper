# 판매순위 갱신 프로세스

## 목적

국내 차량 판매순위 TOP50을 월간 기준으로 갱신하고, `vehicle_master.csv`의 순위와 판매대수를 자동 반영한다.

## 입력

- 월간 판매집계 CSV
- 필수 컬럼: `brand`, `model`
- 권장 컬럼: `rank`, `units_sold`, `vehicle`

## 처리 순서

1. 원본 CSV를 읽는다.
2. `brand + model` 기준으로 `vehicle_master.csv`의 기존 행을 매칭한다.
3. `rank`와 `units_sold`를 갱신한다.
4. 이전 `rank`와 비교해 `rank_change`를 계산한다.
5. 갱신본을 `vehicle_master.csv`에 저장하고, 스냅샷을 `data/sales_snapshot/history/`에 보관한다.
6. 순위 변동이 있을 때만 후속 작업과 알림 갱신을 실행한다.
7. 변경 내역은 `data/notifications.json` 상단 알림으로 추가한다.

## 참고 소스

- 판매순위 원천: 월간 판매집계 CSV 또는 내부 정리본
- 공홈 확인 원천: 제조사 공식 홈페이지, 다운로드 센터, 구매/견적 페이지
- 알림 원천: 공개 뉴스 RSS
- 링크 검증 원천: 공식 가격표 PDF, 모델 안내 페이지
- 후속 작업: 순위 변동이 있는 경우에만 `update_notifications.py`와 `check_price_links.py`를 실행

## 실행 예시

```powershell
python scripts\update_sales_rankings.py --input data\sales_snapshot\monthly_sales.csv
```
