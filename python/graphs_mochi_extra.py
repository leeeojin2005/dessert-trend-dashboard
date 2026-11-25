"""
모찌 그래프 2개 보충 (대시보드에서 비어 있던 자리)
  4번  검색량 vs 매장 수 시차  → images/g04_lag_mochi.png
  9번  지역별 개업 시기        → images/g09_region_mochi.png
입력: raw/search_trend_all.json, data/monthly_counts.csv,
      data/trend_points.json, data/stores_clean.csv
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"

fonts = {f.name for f in font_manager.fontManager.ttflist}
for name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK JP"]:
    if name in fonts:
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"],
              rc={"axes.unicode_minus": False})

MOCHI = "#5aa469"


def save(name):
    plt.savefig(IMG / name, dpi=150, bbox_inches="tight")
    plt.close("all")
    print("저장:", name)


search = pd.DataFrame(json.loads((ROOT / "raw" / "search_trend_all.json")
                                 .read_text(encoding="utf-8"))["data"])
monthly = pd.read_csv(ROOT / "data" / "monthly_counts.csv", encoding="utf-8-sig")
points = json.loads((ROOT / "data" / "trend_points.json").read_text(encoding="utf-8"))

# ───────── 4번: 검색량 vs 매장 수 시차 ─────────
# 팀원이 만든 다른 아이템 그래프와 같은 형식 (둘 다 최고점 대비 %)
FROM = "2024-01"
g = monthly[(monthly["item"] == "모찌") & (monthly["month"] >= FROM)].reset_index(drop=True)
s = search[search["month"] >= FROM].reset_index(drop=True)
g["store_pct"] = g["operating"] / g["operating"].max() * 100
s["search_pct"] = s["모찌"] / s["모찌"].max() * 100
x = pd.to_datetime(g["month"])

plt.figure(figsize=(10, 5.5))
ax = plt.gca()
ax.plot(x, s["search_pct"], color="#808080", lw=2.2, label="검색량")
ax.plot(x, g["store_pct"], color=MOCHI, lw=2.2, label="영업 매장 수")

peak_s = pd.to_datetime(s.loc[s["search_pct"].idxmax(), "month"])
peak_g = pd.to_datetime(g.loc[g["store_pct"].idxmax(), "month"])
ax.axvline(peak_s, color="#808080", ls="--", lw=1.2)
ax.axvline(peak_g, color=MOCHI, ls="--", lw=1.2)
ax.annotate("검색·매장 모두 아직 상승 중\n(정점 미도달 → 시차 측정 불가)",
            xy=(0.97, 0.12), xycoords="axes fraction", ha="right", fontsize=10,
            color="#4a4a4a",
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#c9c2bb"))

ax.set(title="모찌 검색량 vs 영업 매장 수 시차", xlabel="월", ylabel="최고점 대비 (%)",
       ylim=(0, 112))
ax.legend(loc="upper left")
save("g04_lag_mochi.png")

# ───────── 9번: 지역별 개업 시기 ─────────
# 모찌는 유행 시작이 2026-08이라 반기 단위로는 한 칸뿐 → 월 단위로 나눔
st = pd.read_csv(ROOT / "data" / "stores_clean.csv", parse_dates=["open"])
m = st[st["item"] == "모찌"].copy()
m["region"] = m["sido"].str[:2] + " " + m["sigungu"]
m["ym"] = m["open"].dt.strftime("%Y-%m")

t = pd.crosstab(m["region"], m["ym"])
pos = pd.Series(range(len(t.columns)), index=t.columns)
t = t.loc[((t * pos).sum(axis=1) / t.sum(axis=1)).sort_values().index]

plt.figure(figsize=(6.2, 5.8))
ax = sns.heatmap(t, cmap="Greens", vmin=0, linewidths=0.5, linecolor="white",
                 annot=True, fmt="d", annot_kws={"size": 10},
                 cbar=False)
ax.set(title=f"모찌: 시군구별 월간 개업 수 (전체 {len(m)}곳)",
       xlabel="개업 시기 (월)", ylabel="")
save("g09_region_mochi.png")

print("\n모찌 월별 개업:", m.groupby("ym").size().to_dict())
print("지역 수:", m["region"].nunique())
