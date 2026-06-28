# 차량 이미지 보강 체크리스트

## 현재 상태

- 기준 파일: `vehicle_master.csv`
- 검토 파일: `data/vehicle_image_review.csv`
- 앱 노출 조건: `image_review_status=approved` 이면서 `image_source_type`이 `official_newsroom`, `official_site`, `official_press_release`, `manual` 중 하나
- 승인 이미지: 48개
- 보강 필요 이미지: 1개

## 보강 원칙

1. 제조사 공식 홈페이지, 공식 뉴스룸, 공식 보도자료 이미지를 우선 사용한다.
2. 위키미디어, 위키백과, 출처가 불명확한 이미지 URL은 사용하지 않는다.
3. 이미지 URL을 넣은 뒤 `image_source_url`, `image_source_type`, `image_review_status`를 함께 채운다.
4. `scripts/update_vehicle_images.py --write` 실행 후 `data/vehicle_image_review.csv`에서 상태가 `approved`인지 확인한다.

## 보강 필요 차량

| 순위 | 차량 | 현재 상태 | 권장 액션 |
| ---: | --- | --- | --- |
| 41 | KGM 무쏘 EV | needs_source_type | 현재 `press_photo` 출처라 앱에서 숨김. 공식 사이트, 공식 뉴스룸, 공식 보도자료, 또는 수동 승인 이미지로 교체 필요 |

## 확인 명령어

```powershell
python scripts\update_vehicle_images.py --write
```
