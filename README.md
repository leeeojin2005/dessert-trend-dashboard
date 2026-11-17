# 유행 디저트 카피캣 매장 분석 대시보드

SNS 유행 디저트 카피캣 매장의 상권 전이 및 생존 주기 분석 (수도권, 2016–2026)
탕후루 · 마라탕 · 요아정의 패턴으로 모찌의 유행 기간을 예측합니다.

**대시보드:** https://leeeojin2005.github.io/dessert-trend-dashboard/

## 폴더
| 폴더 | 내용 |
|---|---|
| `raw/` | 원본 데이터 (큰 CSV는 GitHub에 올리지 않고 드라이브로 공유) |
| `python/` | 수집 · 전처리 · 그래프 코드 |
| `images/` | seaborn 그래프 PNG |
| `data/` | 전처리 결과 + 대시보드용 JSON |
| `index.html`, `style.css`, `main.js` | 웹 대시보드 |

## 코드 실행 순서
```
python/collect_license.py      # 1. 인허가 데이터 수집 (API 키 필요)
python/collect_general.py      #    일반음식점 지역별 수집
python/check_counts.py         #    아이템별 매장 수 확인
python/clean_stores.py         # 2. 전처리 → data/stores_clean.csv 등
python/graphs_1to3.py          # 3. 그래프 1·2·3·11
python/graphs_7to10.py         #    그래프 7·8·9·10
python/build_dashboard_data.py # 4. data/dashboard.json 생성
```
데이터가 바뀌면 2 → 3 → 4 순서로 다시 실행하면 대시보드가 자동으로 갱신됩니다.

## 그래프
| # | 제목 | seaborn | 담당 |
|---|---|---|---|
| 1 | 디저트별 검색 관심도 추이 | lineplot | 어진 |
| 2 | 유행 생애 곡선 비교 | lineplot | 어진 |
| 3 | 월별 영업 중인 매장 수 | lineplot | 어진 |
| 4 | 검색량 vs 매장 수 시차 | lineplot | sungin0415 |
| 5 | 아이템별 폐업률 | barplot | sungin0415 |
| 6 | 생존 일수 분포 | boxplot | sungin0415 |
| 7 | 폐업까지 걸린 기간 | ecdfplot | 어진 |
| 8 | 진입 시기별 1년 내 폐업률 | catplot | 어진 |
| 9 | 지역별 개업 시기 | heatmap | 어진 |
| 10 | 1인 가구 비율과 매장 수 | regplot | 어진 |
| 11 | 유행 시작 후 첫 3개월 개업 수 | barplot | 어진 |

이미지 파일 이름은 `g01_search.png` 처럼 영문으로 통일했습니다. (한글 파일명은 웹에서 깨질 수 있음)

## 대시보드 열어보는 법
`index.html` 을 더블클릭하면 JSON을 못 읽습니다.
- VS Code / PyCharm 의 **Live Server** 로 열거나
- GitHub Pages 주소로 접속하세요.

## 팀 규칙
1. 작업 전에 꼭 Pull (`Ctrl+T`)
2. 커밋 메시지는 한글로 짧게
3. `api_key.txt` 와 원본 CSV 는 절대 올리지 않기
