"""
대시보드가 읽을 JSON 하나 만들기
입력: data/stores_clean.csv, data/monthly_counts.csv, data/trend_points.json,
      raw/search_trend_all.json
출력: data/dashboard.json
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

ORDER = ["탕후루", "마라탕", "요아정", "모찌"]
KEY = {"탕후루": "tanghulu", "마라탕": "malatang", "요아정": "yoajung", "모찌": "mochi"}
COLORS = {"탕후루": "#e4572e", "마라탕": "#f3a712", "요아정": "#e88eb4", "모찌": "#5aa469"}
LABEL = {"탕후루": "반짝 유행 (끝남)", "마라탕": "비교군 · 정착형", "요아정": "관심은 식고 매장은 유지",
         "모찌": "이제 시작 (예측 대상)"}

stores = pd.read_csv(DATA / "stores_clean.csv", parse_dates=["open", "close"])
monthly = pd.read_csv(DATA / "monthly_counts.csv", encoding="utf-8-sig")
points = json.loads((DATA / "trend_points.json").read_text(encoding="utf-8"))
search = pd.DataFrame(json.loads((ROOT / "raw" / "search_trend_all.json")
                                 .read_text(encoding="utf-8"))["data"])

months = sorted(monthly["month"].unique())
s_by_month = search.set_index("month")

items = {}
for name in ORDER:
    g = stores[stores["item"] == name]
    m = monthly[monthly["item"] == name].set_index("month")
    p = points[name]
    peak_search = search.loc[search[name].idxmax(), "month"]
    first3 = m.loc[[x for x in months if x >= p["start"]][:3], "opened"].sum()

    items[name] = {
        "key": KEY[name], "color": COLORS[name], "label": LABEL[name], "is_ref": name == "마라탕",
        "stores": int(len(g)),
        "closed": int(g["closed"].sum()),
        "close_rate": round(float(g["closed"].mean()) * 100, 1),
        "avg_days": int(g["survival_days"].mean()),
        "median_days": int(g["survival_days"].median()),
        "search_peak": peak_search,
        "search_peak_value": round(float(search[name].max()), 1),
        "search_now": round(float(search[name].iloc[-1]), 1),
        "start": p["start"], "peak": p["peak"], "peak_count": p["peak_count"],
        "decline": p["decline"], "now_count": p["now_count"],
        "start_source": p.get("start_source", "매장 수"),
        "lag_months": int((pd.Period(p["peak"], "M") - pd.Period(peak_search, "M")).n),
        "first3_opened": int(first3),
        "stage": g["stage"].value_counts().to_dict(),
        "series": [
            {"m": mm,
             "operating": int(m.loc[mm, "operating"]) if mm in m.index else 0,
             "opened": int(m.loc[mm, "opened"]) if mm in m.index else 0,
             "closed": int(m.loc[mm, "closed"]) if mm in m.index else 0,
             "search": round(float(s_by_month.loc[mm, name]), 2) if mm in s_by_month.index else None}
            for mm in months
        ],
    }

# 지역 상위 10곳
stores["region"] = stores["sido"].str[:2] + " " + stores["sigungu"]
regions = {}
for name in ORDER:
    g = stores[stores["item"] == name]
    regions[name] = (g["region"].value_counts().head(10)
                     .rename_axis("region").reset_index(name="n").to_dict("records"))

# 매장 검색 표에 쓸 목록 (용량을 줄이려고 키를 짧게)
tbl = stores.sort_values(["item", "open"])
store_list = [{
    "n": r["name"], "i": KEY[r["item"]], "r": r["region"],
    "o": r["open"].strftime("%Y-%m-%d"),
    "c": None if pd.isna(r["close"]) else r["close"].strftime("%Y-%m-%d"),
    "d": int(r["survival_days"]), "s": r["stage"],
} for _, r in tbl.iterrows()]

# 생애 곡선 (유행 시작 0개월 기준, 최고점 대비 %) — 모찌 예측 시나리오에 사용
lifecycle = {}
for name in ORDER:
    p = points[name]
    g = monthly[monthly["item"] == name].copy()
    start = pd.Period(p["start"], "M")
    g["e"] = g["month"].apply(lambda m: (pd.Period(m, "M") - start).n)
    g = g[g["e"] >= 0]
    mx = g["operating"].max()
    lifecycle[KEY[name]] = {
        "pct": [round(v / mx * 100, 2) for v in g["operating"]],
        "abs": [int(v) for v in g["operating"]],
    }

out = {
    "months": months,
    "items": items,
    "regions": regions,
    "store_list": store_list,
    "lifecycle": lifecycle,
    "total_stores": int(len(stores)),
    "charts": [
        {"id": 1, "cat": "검색량", "title": "메뉴별 검색 관심도 추이",
         "img": "images/g01_search.png", "per_item": False,
         "desc": "네 키워드를 한 번에 조회한 공통 기준 지수라서 서로 크기를 비교할 수 있다. 마라탕이 2019년 7월 가장 높았고(일시적 급등), 탕후루는 2023년 8월, 요아정은 2024년 8월에 정점을 찍었다. 모찌는 2026년 10월 현재 올라오는 중이지만 크기는 마라탕 최고점의 2% 수준이다."},
        {"id": 2, "cat": "검색량", "title": "유행 생애 곡선 비교",
         "img": "images/g02_lifecycle.png", "per_item": False,
         "desc": "유행 시작을 0개월로 맞춰 매장 수 곡선을 겹쳤다. 탕후루는 8개월 만에 정점을 찍고 급락했고, 요아정은 30개월에 걸쳐 올라 아직 유지 중이며, 마라탕은 56개월 동안 완만히 올랐다. 모찌는 현재 3개월째로 아직 어느 길을 갈지 판단하기 이르다."},
        {"id": 3, "cat": "매장", "title": "월별 영업 중인 매장 수",
         "img": "images/g03_stores.png", "per_item": True,
         "img_item": "images/g03_stores_{key}.png",
         "desc": "수도권에서 그 달에 영업 중이던 카피캣 매장 수다. 탕후루는 741곳까지 늘었다가 64곳으로 줄었고, 마라탕은 1,608곳까지 오른 뒤 완만히 감소 중이다. 요아정은 294곳에서 거의 그대로 유지되고 있다."},
        {"id": 4, "cat": "검색량", "title": "검색량 vs 매장 수 시차",
         "img": "images/g04_lag_tanghulu.png", "per_item": True,
         "img_item": "images/g04_lag_{key}.png",
         "desc": "검색 관심이 정점을 찍은 뒤 실제 매장 수가 정점에 도달하기까지의 시차를 보여준다. 탕후루는 3개월, 요아정은 23개월, 마라탕은 58개월로 메뉴마다 크게 달랐다. 반짝 유행일수록 시차가 짧다."},
        {"id": 5, "cat": "생존", "title": "아이템별 폐업률",
         "img": "images/g05_closerate.png", "per_item": False,
         "desc": "카피캣 매장 중 폐업한 비율이다. 탕후루는 92%가 문을 닫았고, 마라탕은 40%, 요아정은 11%에 그쳤다. 같은 유행이라도 결과가 완전히 달랐다. 마라탕은 디저트가 아닌 비교군으로, 유행이 정착했을 때의 기준선 역할을 한다."},
        {"id": 6, "cat": "생존", "title": "생존 일수 분포",
         "img": "images/g06_survival_box.png", "per_item": False,
         "desc": "매장이 실제로 버틴 일수를 상자그림으로 나타냈다. 마라탕은 중앙값이 약 1,100일로 가장 길고, 탕후루는 약 490일로 짧다. 요아정은 1년 미만에 닫은 이상치가 아래쪽에 몰려 있다."},
        {"id": 7, "cat": "생존", "title": "폐업까지 걸린 기간",
         "img": "images/g07_ecdf.png", "per_item": False,
         "desc": "폐업한 가게만 모아 개업 후 며칠 만에 닫았는지를 누적 비율로 그렸다. 탕후루는 폐업 매장의 절반이 약 15개월(462일) 안에 문을 닫았고, 마라탕은 중앙값이 약 2년(723일)으로 훨씬 완만하다."},
        {"id": 8, "cat": "생존", "title": "진입 시기별 1년 내 폐업률",
         "img": "images/g08_stage.png", "per_item": False,
         "desc": "개업 후 1년이 지난 가게만 추려 1년 안에 폐업한 비율을 비교했다. 탕후루는 쇠퇴기에 들어간 가게의 44%가 1년도 못 버텼다(초기 27%). 마라탕은 어느 시기든 8~13%로 낮아, 정착한 메뉴는 진입 시기의 영향을 덜 받는다."},
        {"id": 9, "cat": "상권", "title": "지역별 개업 시기",
         "img": "images/g09_region_tanghulu.png", "per_item": True,
         "img_item": "images/g09_region_{key}.png",
         "desc": "매장이 많은 20개 시군구에서 개업이 어느 반기에 몰렸는지를 색으로 나타냈다. 탕후루는 용인·수원·평택·강서구에서 2023년 상반기에 먼저 퍼졌고, 시흥·안산·부천 등은 하반기에 몰렸다. 유행이 한 번에 퍼진 게 아니라 지역을 옮겨가며 번진 '상권 전이'가 보인다."},
        {"id": 10, "cat": "상권", "title": "1인 가구 비율과 매장 수",
         "img": "images/g10_single.png", "per_item": False,
         "desc": "서울·경기 시군구별 1인 가구 비율(2025년, KOSIS)과 가구 1만 개당 매장 수의 관계다. 상관계수가 0.07로 거의 관계가 없었다. 오히려 가구당 매장이 많은 곳은 시흥·김포·화성·오산 같은 경기 신도시로, 유행 디저트는 1인 가구보다 신도시 상권으로 퍼진 것으로 보인다."},
        {"id": 11, "cat": "예측", "title": "유행 시작 후 첫 3개월 개업 수",
         "img": "images/g11_mochi_first3.png", "per_item": False,
         "desc": "유행이 시작된 뒤 첫 3개월 동안 문을 연 매장 수다. 탕후루 74곳, 마라탕 110곳, 요아정 23곳에 비해 모찌는 16곳으로 가장 완만하다. 탕후루처럼 폭발적으로 번지는 양상은 아직 나타나지 않았다."},
    ],
}

(DATA / "dashboard.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("저장: data/dashboard.json")
for n, v in items.items():
    print(f"  {n}: {v['stores']}곳 | 폐업 {v['close_rate']}% | 검색피크 {v['search_peak']} "
          f"→ 매장피크 {v['peak']} ({v['lag_months']}개월) | 첫3개월 {v['first3_opened']}곳")
