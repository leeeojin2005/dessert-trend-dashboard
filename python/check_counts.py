from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "raw"
lines = []

def log(t=""):
    print(t)
    lines.append(str(t))

for file in sorted(RAW.glob("*_sudo.csv")):
    df = pd.read_csv(file, dtype=str)
    log(f"\n===== {file.name} (수도권 {len(df)}건) =====")
    for item, g in df.groupby("item"):
        closed = g["CLSBIZ_YMD"].notna().sum()
        log(f"- {item}: {len(g)}개 | 폐업 {closed}개 | 영업 중 {len(g) - closed}개 "
            f"| 개업일 {g['LCPMT_YMD'].min()} ~ {g['LCPMT_YMD'].max()}")
        log(f"    예시: {g['BPLC_NM'].sample(min(5, len(g)), random_state=0).tolist()}")

(RAW / "check_report.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n저장: raw/check_report.txt")