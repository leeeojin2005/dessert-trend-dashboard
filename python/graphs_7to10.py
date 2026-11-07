from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import PercentFormatter

# ── 기본 설정 ──
ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"
IMG.mkdir(exist_ok=True)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", font="Malgun Gothic", rc={"axes.unicode_minus": False})

TODAY = pd.Timestamp("2026-10-31")
COLORS = {"탕후루": "#e4572e", "마라탕": "#f3a712", "요아정": "#e88eb4", "모찌": "#5aa469"}

# ── 데이터 불러오기 ──
df = pd.read_csv(ROOT / "data" / "stores_clean.csv", parse_dates=["open", "close"])
df = df[df["sido"].isin(["서울특별시", "경기도", "인천광역시"])]


def save(name):
    plt.savefig(IMG / name, dpi=150, bbox_inches="tight")
    plt.close("all")
    print("저장:", name)


# ── 7. 폐업까지 걸린 기간 (ecdfplot) ──
closed = df[df["closed"] & (df["item"] != "모찌")]
plt.figure(figsize=(9, 5))
ax = sns.ecdfplot(data=closed, x="survival_days", hue="item",
                  hue_order=["탕후루", "마라탕", "요아정"], palette=COLORS, linewidth=2.5)
for d, label in [(365, "1년"), (730, "2년")]:
    ax.axvline(d, color="gray", ls="--", lw=1)
    ax.text(d + 15, 0.03, label, color="gray")
ax.set(title="개업에서 폐업하기까지의 기간",
       xlabel="개업 후 폐업까지 걸린 일수", ylabel="누적 비율 (폐업 매장 중)", xlim=(0, 2500))
ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
ax.get_legend().set_title("")
save("graph07_폐업까지기간.png")

# ── 8. 진입 시기별 1년 내 폐업률 (catplot) ──
old = df[(df["open"] <= TODAY - pd.Timedelta(days=365)) & (df["item"] != "모찌")].copy()
old["closed_1y"] = old["closed"] & (old["survival_days"] <= 365)
g = sns.catplot(data=old, x="stage", y="closed_1y", hue="item", kind="bar",
                order=["초기", "성숙기", "쇠퇴기"], hue_order=["탕후루", "마라탕", "요아정"],
                palette=COLORS, errorbar=None, height=5, aspect=1.6, legend_out=False)
g.ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
g.set(title="진입 시기별 개업 1년 내 폐업률",
      xlabel="진입 시기", ylabel="1년 내 폐업률")
for c in g.ax.containers:
    g.ax.bar_label(c, labels=[f"{v:.0%}" if v == v and v > 0 else "" for v in c.datavalues], padding=2)
g.ax.get_legend().set_title("")
save("graph08_진입시기폐업률.png")

# ── 9. 지역별 개업 시기 (heatmap) ──
df["region"] = df["sido"].str[:2] + " " + df["sigungu"]
df["half"] = df["open"].dt.year.astype(str) + "-" + df["open"].dt.month.map(lambda m: "상" if m <= 6 else "하")
for item, start in [("탕후루", 2023), ("마라탕", 2019), ("요아정", 2024)]:
    g = df[(df["item"] == item) & (df["open"].dt.year >= start)]
    top = g["region"].value_counts().head(20).index
    t = pd.crosstab(g[g["region"].isin(top)]["region"], g["half"])
    share = t.div(t.sum(axis=1), axis=0)
    pos = pd.Series(range(len(share.columns)), index=share.columns)
    share = share.loc[(share * pos).sum(axis=1).sort_values().index]
    plt.figure(figsize=(max(7, len(share.columns) * 0.7), 8))
    ax = sns.heatmap(share, cmap="Reds", vmin=0, linewidths=0.4, linecolor="white",
                     cbar_kws={"label": "그 지역 개업 중 비율", "format": PercentFormatter(1)})
    ax.set(title=f"{item}: 시군구별 반기 개업 비율 (매장 수 상위 20곳)",
           xlabel="개업 시기 (반기)", ylabel="")
    save(f"graph09_지역별개업시기_{item}.png")

# ── 10. 1인 가구 비율 vs 매장 수 (regplot) ──
k = pd.read_csv(ROOT / "raw" / "Kosis_single.csv", encoding="utf-8-sig")
k = k[k["시/군/구"] != "소계"].rename(columns={"시/도": "sido", "시/군/구": "sigungu"})
cnt = df.groupby(["sido", "sigungu"]).size().rename("stores").reset_index()
m = k.merge(cnt, on=["sido", "sigungu"], how="left").fillna({"stores": 0})
m["per10k"] = m["stores"] / m["일반가구수"] * 10000
r = m["1인가구비율(%)"].corr(m["per10k"])

plt.figure(figsize=(9, 6))
ax = sns.regplot(data=m, x="1인가구비율(%)", y="per10k",
                 scatter_kws={"s": 45, "alpha": 0.7}, line_kws={"color": "#e4572e"})
for _, row in m.nlargest(5, "per10k").iterrows():
    ax.annotate(row["sigungu"], (row["1인가구비율(%)"], row["per10k"]),
                xytext=(5, 3), textcoords="offset points", fontsize=9)
ax.set(title=f"시군구별 1인 가구 비율과 가구 1만 개당 매장 수 (r = {r:.2f})",
       xlabel="1인 가구 비율 (%, 2025년)", ylabel="가구 1만 개당 카피캣 매장 수")
save("graph10_1인가구vs매장.png")