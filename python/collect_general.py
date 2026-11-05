import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
PARTS = RAW / "general_parts"
PARTS.mkdir(exist_ok=True)

API_KEY = (ROOT / "api_key.txt").read_text(encoding="utf-8").split()[0]
URL = "https://apis.data.go.kr/1741000/general_restaurants/info"

KEYWORDS = {
    "마라탕": ["마라탕", "마라샹궈"],
}

KEEP = ["MNG_NO", "BPLC_NM", "LCPMT_YMD", "CLSBIZ_YMD", "SALS_STTS_NM",
        "DTL_SALS_STTS_NM", "BZSTAT_SE_NM", "ROAD_NM_ADDR", "LOTNO_ADDR",
        "CRD_INFO_X", "CRD_INFO_Y", "OPN_ATMY_GRP_CD"]

rest = pd.read_csv(RAW / "rest_food_sudo.csv", dtype=str)
CODES = sorted(rest["OPN_ATMY_GRP_CD"].dropna().unique())


def get(params):
    params = {"serviceKey": API_KEY, "returnType": "json", "numOfRows": 100, **params}
    for attempt in range(3):
        try:
            res = requests.get(URL, params=params, timeout=120)
            res.raise_for_status()
            body = res.json()["response"].get("body", {})
            items = body.get("items", {})
            items = items.get("item", []) if isinstance(items, dict) else items
            return int(body.get("totalCount", 0)), items or []
        except Exception as e:
            print(f"    실패 ({attempt + 1}/3): {str(e)[:60]}")
            time.sleep(10)
    return None


def fetch_region(code):
    rows = []
    for item, words in KEYWORDS.items():
        for kw in words:
            cond = {"cond[OPN_ATMY_GRP_CD::EQ]": code, "cond[BPLC_NM::LIKE]": kw}
            first = get({"pageNo": 1, **cond})
            if first is None:
                return None
            total, items = first
            got = list(items)
            for page in range(2, (total + 99) // 100 + 1):
                more = get({"pageNo": page, **cond})
                if more is None:
                    return None
                got.extend(more[1])
            for r in got:
                r["item"] = item
            rows.extend(got)
    return rows


todo = [c for c in CODES if not (PARTS / f"{c}.csv").exists()]
print(f"수도권 {len(CODES)}개 중 남은 지역 {len(todo)}개\n")

for n, code in enumerate(todo, 1):
    rows = fetch_region(code)
    if rows is None:
        print(f"[{n}/{len(todo)}] {code}: 실패 → 다음에 다시 실행하면 이어서 받아요")
        continue
    pd.DataFrame(rows, columns=KEEP + ["item"]).to_csv(
        PARTS / f"{code}.csv", index=False, encoding="utf-8-sig")
    print(f"[{n}/{len(todo)}] {code}: {len(rows)}건 저장")

done = sorted(PARTS.glob("*.csv"))
missing = [c for c in CODES if not (PARTS / f"{c}.csv").exists()]
df = pd.concat([pd.read_csv(f, dtype=str) for f in done], ignore_index=True) if done else pd.DataFrame()
if not df.empty:
    df = df.drop_duplicates(subset=["MNG_NO", "item"])
    df.to_csv(RAW / "general_food_sudo.csv", index=False, encoding="utf-8-sig")
print(f"\n완료 {len(done)}/{len(CODES)}개 지역, 마라탕 {len(df)}건 → raw/general_food_sudo.csv")
if missing:
    print(f"아직 못 받은 지역 {len(missing)}개: {missing}")
    print("→ 잠시 후 이 파일을 다시 실행하면 이 지역들만 받아요")
else:
    print("모든 지역 완료!")