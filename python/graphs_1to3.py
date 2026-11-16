"""
그래프 1~3번 (seaborn)
  1. 디저트별 검색량 추이 (lineplot)        - 키워드 공통 기준
  2. 유행 생애 곡선 비교 (lineplot)         - 유행 시작 = 0개월로 맞춰서 겹치기
  3. 월별 영업 매장 수 (lineplot)           - 아이템별 3장 + 전체 1장
입력: raw/search_trend_all.json, data/monthly_counts.csv, data/trend_points.json
출력: images/graph01~03_*.png
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"
IMG.mkdir(exist_ok=True)

# ── 한글 폰트 ──
fonts = {f.name for f in font_manager.fontManager.ttflist}
for name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK JP"]:
    if name in fonts:
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"], rc={"axes.unicode_minus": False})

ORDER = ["탕후루", "마라탕", "요아정", "모찌"]
COLORS = {"탕후루": "#e4572e", "마라탕": "#f3a712", "요아정": "#e88eb4", "모찌": "#5aa469"}


def save(name):
    plt.savefig(IMG / name, dpi=150, bbox_inches="tight")
    plt.close("all")
    print("저장:", name)


# ── 데이터 ──
trend = json.loads((ROOT / "raw" / "search_trend_all.json").read_text(encoding="utf-8"))
search = pd.DataFrame(trend["data"])
search["month_dt"] = pd.to_datetime(search["month"])

monthly = pd.read_csv(ROOT / "data" / "monthly_counts.csv", encoding="utf-8-sig")
monthly["month_dt"] = pd.to_datetime(monthly["month"])
points = json.loads((ROOT / "data" / "trend_points.json").read_text(encoding="utf-8"))

# ───────── 1. 디저트별 검색량 추이 ─────────
# 한 번에 조회한 공통 기준 지수 → 디저트끼리 크기 비교 가능
long = search.melt(id_vars="month_dt", value_vars=ORDER, var_name="item", value_name="search")
plt.figure(figsize=(11, 5.5))
ax = sns.lineplot(data=long, x="month_dt", y="search", hue="item",
                  hue_order=ORDER, palette=COLORS, linewidth=2.2)
# 최고점 표시 (제목과 겹치지 않게 아래쪽으로)
for item in ORDER:
    g = long[long["item"] == item]
    top = g.loc[g["search"].idxmax()]
    ax.annotate(f"{item} 최고 {top['month_dt']:%Y-%m}", (top["month_dt"], top["search"]),
                xytext=(8, -14), textcoords="offset points", ha="left",
                fontsize=9, color=COLORS[item], fontweight="bold")
ax.set(title="디저트별 검색 관심도 추이 (2016~2026)",
       xlabel="", ylabel="검색 관심도 (네 키워드 공통 기준, 최고 = 100)", ylim=(-3, 112))
ax.get_legend().set_title("")
save("graph01_검색량추이.png")

# ───────── 2. 유행 생애 곡선 비교 ─────────
# 유행 시작을 0개월로 맞추고, 누적 개업 수를 최고점 대비 %로 → 모양만 비교
# 모찌는 아직 3개월뿐이라 자기 최고점 기준으로 100%가 돼 오해를 주므로 제외
THREE = ["탕후루", "마라탕", "요아정"]
rows = []
for item in THREE:
    p = points[item]
    g = monthly[monthly["item"] == item].copy()
    start = pd.Period(p["start"], "M")
    g["elapsed"] = (g["month_dt"].dt.to_period("M") - start).apply(lambda x: x.n)
    g = g[g["elapsed"] >= 0]
    g["pct"] = g["operating"] / g["operating"].max() * 100
    rows.append(g)
life = pd.concat(rows)

plt.figure(figsize=(11, 5.5))
ax = sns.lineplot(data=life, x="elapsed", y="pct", hue="item",
                  hue_order=THREE, palette=COLORS, linewidth=2.5)
for item in THREE:
    g = life[life["item"] == item]
    top = g.loc[g["pct"].idxmax()]
    ax.annotate(f"{int(top['elapsed'])}개월", (top["elapsed"], 100),
                xytext=(0, 6), textcoords="offset points", ha="center",
                fontsize=9, color=COLORS[item], fontweight="bold")
ax.axvline(3, color=COLORS["모찌"], ls="--", lw=1.5)
ax.annotate("모찌는 지금 여기 (3개월째)", (3, 8), xytext=(10, 0), textcoords="offset points",
            color=COLORS["모찌"], fontweight="bold", fontsize=10)
ax.set(title="유행 시작을 0개월로 맞춰 겹쳐 보면: 탕후루는 8개월 만에 정점, 마라탕은 56개월",
       xlabel="유행 시작 후 경과 개월", ylabel="매장 수 (각 아이템 최고점 대비 %)",
       xlim=(-2, 90), ylim=(0, 112))
ax.get_legend().set_title("")
save("graph02_유행생애곡선.png")

# ───────── 2-b. 모찌 예측: 유행 시작 후 첫 3개월 개업 수 ─────────
first3 = []
for item, p in points.items():
    g = monthly[monthly["item"] == item].copy()
    start = pd.Period(p["start"], "M")
    g["elapsed"] = (g["month_dt"].dt.to_period("M") - start).apply(lambda x: x.n)
    n = g[(g["elapsed"] >= 0) & (g["elapsed"] <= 2)]["opened"].sum()
    first3.append({"item": item, "opened": int(n)})
f3 = pd.DataFrame(first3)

plt.figure(figsize=(9, 5))
ax = sns.barplot(data=f3, x="item", y="opened", hue="item",
                 order=ORDER, hue_order=ORDER, palette=COLORS, legend=False)
for c in ax.containers:
    ax.bar_label(c, fmt="%d곳", padding=3, fontsize=11)
ax.set(title="유행 시작 후 첫 3개월 동안 문을 연 매장 수: 모찌는 탕후루보다 훨씬 완만하다",
       xlabel="", ylabel="첫 3개월 개업 수")
save("graph11_모찌예측_첫3개월.png")
print("\n[2-b] 첫 3개월 개업 수")
print(f3.to_string(index=False))

# ───────── 3. 월별 영업 매장 수 ─────────
# (1) 전체 한 장
plt.figure(figsize=(11, 5.5))
ax = sns.lineplot(data=monthly, x="month_dt", y="operating", hue="item",
                  hue_order=ORDER, palette=COLORS, linewidth=2.2)
ax.set(title="월별 영업 중인 카피캣 매장 수 (수도권)", xlabel="", ylabel="영업 중인 매장 수")
ax.get_legend().set_title("")
save("graph03_월별매장수.png")

# (2) 아이템별 한 장씩 — 유행 시작·최고점·감퇴 표시
for item in ORDER:
    g = monthly[monthly["item"] == item]
    p = points[item]
    plt.figure(figsize=(10, 5))
    ax = sns.lineplot(data=g, x="month_dt", y="operating", color=COLORS[item], linewidth=2.5)
    marks = [("유행 시작", p["start"], "#888"), ("최고점", p["peak"], COLORS[item])]
    if p["decline"]:
        marks.append(("감퇴 시작", p["decline"], "#555"))
    top = ax.get_ylim()[1]
    for i, (label, month, color) in enumerate(marks):
        x = pd.to_datetime(month)
        ax.axvline(x, color=color, ls="--", lw=1.2)
        ax.annotate(f"{label} {month}", (x, top * (0.95 - i * 0.12)),
                    xytext=(-6, 0), textcoords="offset points",
                    ha="right", fontsize=9, color=color,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.95))
    ax.set(title=f"{item} 월별 영업 매장 수 (최고 {p['peak_count']}곳 → 현재 {p['now_count']}곳)",
           xlabel="", ylabel="영업 중인 매장 수")
    save(f"graph03_월별매장수_{item}.png")

# ── 설명에 쓸 숫자 ──
print("\n[1] 검색 최고 달과 공통 기준 크기")
for item in ORDER:
    top = search.loc[search[item].idxmax()]
    print(f"  {item}: {top['month']} ({top[item]:.1f})")
print("\n[2] 유행 시작 후 최고점까지 걸린 개월")
for item, p in points.items():
    n = (pd.Period(p["peak"], "M") - pd.Period(p["start"], "M")).n
    print(f"  {item}: {n}개월 (시작 {p['start']} → 최고 {p['peak']})")
