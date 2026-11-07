import json
from pathlib import Path

import pandas as pd
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

TODAY = pd.Timestamp("2026-10-31")      # 분석 기준일 (검색량 마지막 달)
DATA_FROM = pd.Timestamp("2016-01-01")  # 검색량 데이터 시작 = 분석 시작
START_RATIO = 0.20                      # 유행 시작: 최고점의 20%
DECLINE_RATIO = 0.05                    # 감퇴 시작: 최고점에서 5% 감소
CONFIRM_MONTHS = 3                      # 감퇴가 3개월 연속 이어져야 인정
MIN_DAYS = 30                           # 30일 안에 폐업 = 팝업으로 보고 제외
POPUP_WORDS = ["한시적", "팝업", "pop-up", "popup"]
# 매장 수로 시작점이 안 잡히는 아이템은 검색량 급등 시점을 직접 지정
START_OVERRIDE = {
    "모찌": "2026-08",
}
# 오탐 제외 목록 (찾을 때마다 추가)
EXCLUDE_NAMES = [
    "이모찌마",   # 찌개집
]

log = []


def say(text=""):
    print(text)
    log.append(str(text))


# 1. 불러오기 + 합치기
frames = []
for file, kind in [("rest_food_sudo.csv", "휴게음식점"), ("general_food_sudo.csv", "일반음식점")]:
    df = pd.read_csv(RAW / file, dtype=str)
    df["업종구분"] = kind
    frames.append(df)
df = pd.concat(frames, ignore_index=True)
say(f"[1] 불러오기: {len(df)}곳")
counts = {"불러오기": df.groupby("item").size()}

df["open"] = pd.to_datetime(df["LCPMT_YMD"], errors="coerce")
df["close"] = pd.to_datetime(df["CLSBIZ_YMD"], errors="coerce")
df["addr"] = df["ROAD_NM_ADDR"].fillna("").where(df["ROAD_NM_ADDR"].notna() & (df["ROAD_NM_ADDR"] != ""),
                                                 df["LOTNO_ADDR"].fillna(""))

# 2. 중복 제거 (같은 가게가 휴게·일반 둘 다 있거나, 검색어 두 개에 걸린 경우)
before = len(df)
df["name_key"] = df["BPLC_NM"].str.replace(r"\s", "", regex=True)
df = df.sort_values("open").drop_duplicates(subset=["item", "name_key", "addr", "open"])
say(f"[2] 중복 제거: -{before - len(df)}곳")

# 3. 오탐 제거
before = len(df)
df = df[~df["BPLC_NM"].isin(EXCLUDE_NAMES)]
say(f"[3] 오탐 제거: -{before - len(df)}곳 (목록 {len(EXCLUDE_NAMES)}개)")

# 4. 날짜 없는 가게 제거
before = len(df)
df = df[df["open"].notna()]
say(f"[4] 개업일 없음: -{before - len(df)}곳")

# 5. 생존 일수
df["closed"] = df["close"].notna()
df["survival_days"] = ((df["close"].fillna(TODAY)) - df["open"]).dt.days

# 6. 팝업 제거
before = len(df)
popup_name = df["BPLC_NM"].str.contains("|".join(POPUP_WORDS), case=False, na=False)
popup_short = df["closed"] & (df["survival_days"] < MIN_DAYS)
df = df[~(popup_name | popup_short)]
say(f"[6] 팝업 제거: -{before - len(df)}곳 (이름 {popup_name.sum()}, {MIN_DAYS}일 미만 {popup_short.sum()})")

# 7. 분석 기간 이전 개업 제거 (유행 전부터 있던 가게, 또는 인허가일이 옛날로 남은 가게)
before = len(df)
old = df[df["open"] < DATA_FROM]
df = df[df["open"] >= DATA_FROM]
say(f"[7] {DATA_FROM:%Y-%m} 이전 개업: -{before - len(df)}곳")
counts["분석 기간 이전 개업"] = old.groupby("item").size()

# 8. 월별 영업 매장 수
months = pd.period_range(DATA_FROM, TODAY, freq="M")
rows = []
for item, g in df.groupby("item"):
    o = g["open"].dt.to_period("M")
    c = g["close"].dt.to_period("M")
    for m in months:
        rows.append({
            "item": item,
            "month": str(m),
            "operating": int(((o <= m) & (c.isna() | (c > m))).sum()),
            "opened": int((o == m).sum()),
            "closed": int((c == m).sum()),
        })
monthly = pd.DataFrame(rows)

# 9. 유행 시작 · 최고점 · 감퇴 시점
points = {}
for item, g in monthly.groupby("item"):
    g = g.reset_index(drop=True)
    peak_i = int(g["operating"].idxmax())
    peak = int(g.loc[peak_i, "operating"])
    start_i = int(g.index[g["operating"] >= peak * START_RATIO][0])

    decline = None
    limit = peak * (1 - DECLINE_RATIO)
    after = g.loc[peak_i + 1:, "operating"]
    for i in after.index:
        window = g.loc[i:i + CONFIRM_MONTHS - 1, "operating"]
        if len(window) == CONFIRM_MONTHS and (window <= limit).all():
            decline = g.loc[i, "month"]
            break

    points[item] = {
        "start": g.loc[start_i, "month"],
        "peak": g.loc[peak_i, "month"],
        "peak_count": peak,
        "decline": decline,
        "now_count": int(g["operating"].iloc[-1]),
    }

for item, month in START_OVERRIDE.items():
    if item in points:
        points[item]["start"] = month
        points[item]["start_source"] = "검색량"

# 10. 카피캣: 유행 시작 이후 개업한 가게만
before = len(df)
df["start"] = pd.to_datetime(df["item"].map({k: v["start"] for k, v in points.items()}))
pre = df[df["open"] < df["start"]]
df = df[df["open"] >= df["start"]]
say(f"[10] 유행 시작 전 개업: -{before - len(df)}곳")
counts["유행 시작 전 개업"] = pre.groupby("item").size()


# 11. 진입 시기 (초기 / 성숙기 / 쇠퇴기)
def stage(row):
    p = points[row["item"]]
    m = row["open"].to_period("M")
    if m < pd.Period(p["peak"], "M"):
        return "초기"
    if p["decline"] is None or m < pd.Period(p["decline"], "M"):
        return "성숙기"
    return "쇠퇴기"


df["stage"] = df.apply(stage, axis=1)

# 12. 좌표 변환 (EPSG:5174 → 위경도)
tf = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
x = pd.to_numeric(df["CRD_INFO_X"], errors="coerce")
y = pd.to_numeric(df["CRD_INFO_Y"], errors="coerce")
ok = x.notna() & y.notna()
lng, lat = tf.transform(x[ok].values, y[ok].values)
df.loc[ok, "lng"] = lng
df.loc[ok, "lat"] = lat

# 13. 시도 · 시군구
parts = df["addr"].str.split()
df["sido"] = parts.str[0]
df["sigungu"] = parts.str[1]

# 14. 저장
cols = ["item", "BPLC_NM", "업종구분", "BZSTAT_SE_NM", "open", "close", "closed",
        "survival_days", "stage", "sido", "sigungu", "addr", "lat", "lng", "MNG_NO"]
clean = df[cols].rename(columns={"BPLC_NM": "name", "BZSTAT_SE_NM": "biztype", "업종구분": "kind"})
clean["open"] = clean["open"].dt.strftime("%Y-%m-%d")
clean["close"] = clean["close"].dt.strftime("%Y-%m-%d")
clean.sort_values(["item", "open"]).to_csv(OUT / "stores_clean.csv", index=False, encoding="utf-8-sig")
monthly.to_csv(OUT / "monthly_counts.csv", index=False, encoding="utf-8-sig")
(OUT / "trend_points.json").write_text(json.dumps(points, ensure_ascii=False, indent=2), encoding="utf-8")

# 15. 오탐 의심 목록: 아이템마다 흔하지 않은 업태 (해당 아이템의 5% 미만)
share = clean.groupby(["item", "biztype"])["name"].transform("count") / clean.groupby("item")["name"].transform("count")
sus = clean[share < 0.05][["item", "name", "biztype", "kind", "addr", "open"]]
sus.to_csv(RAW / "suspicious.csv", index=False, encoding="utf-8-sig")

# 16. 요약
say("\n===== 최종 결과 =====")
for item, p in points.items():
    g = clean[clean["item"] == item]
    say(f"[{item}] {len(g)}곳 | 폐업률 {g['closed'].mean():.0%} | 평균 생존 {g['survival_days'].mean():.0f}일")
    say(f"   유행 시작 {p['start']} → 최고점 {p['peak']} ({p['peak_count']}곳) → 감퇴 {p['decline'] or '아직 없음'} | 지금 {p['now_count']}곳")
    say(f"   진입 시기: {g['stage'].value_counts().to_dict()}")
say(f"\n좌표 변환 성공 {clean['lat'].notna().sum()}/{len(clean)}곳")
say(f"오탐 의심 {len(sus)}곳 → raw/suspicious.csv 확인")

summary = pd.DataFrame(counts).fillna(0).astype(int)
say("\n제외된 가게 수 (아이템별):")
say(summary.to_string())

(RAW / "clean_report.txt").write_text("\n".join(log), encoding="utf-8")
say("\n저장: data/stores_clean.csv, data/monthly_counts.csv, data/trend_points.json, raw/clean_report.txt")