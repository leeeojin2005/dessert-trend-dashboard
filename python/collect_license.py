import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
RAW.mkdir(exist_ok=True)

API_KEY = (ROOT / "api_key.txt").read_text(encoding="utf-8").split()[0]

SERVICES = {
    # "rest_food": "https://apis.data.go.kr/1741000/rest_cafes/info",
    "general_food": "https://apis.data.go.kr/1741000/general_restaurants/info",
}

KEYWORDS = {
    "마라탕": ["마라탕", "마라샹궈"],
    "요아정": ["요아정", "요거트아이스크림의정석"],
    "탕후루": ["탕후루"],
    "모찌": ["모찌"],
}

KEEP = ["MNG_NO", "BPLC_NM", "LCPMT_YMD", "CLSBIZ_YMD", "SALS_STTS_NM",
        "DTL_SALS_STTS_NM", "BZSTAT_SE_NM", "ROAD_NM_ADDR", "LOTNO_ADDR",
        "CRD_INFO_X", "CRD_INFO_Y", "OPN_ATMY_GRP_CD"]

SUDO = ("서울", "경기", "인천")

# "test": 상호명 검색이 되는지 시험 / "collect": 실제 수집
MODE = "collect"

ROWS_PER_PAGE = 100


def get(url, params):
    params = {"serviceKey": API_KEY, "returnType": "json", **params}
    for attempt in range(5):
        try:
            res = requests.get(url, params=params, timeout=300)
            res.raise_for_status()
            body = res.json()["response"].get("body", {})
            items = body.get("items", {})
            items = items.get("item", []) if isinstance(items, dict) else items
            return int(body.get("totalCount", 0)), items or []
        except Exception as e:
            print(f"  실패 ({attempt + 1}/3): {e}")
            time.sleep(10)
    raise RuntimeError(f"요청 실패. 응답: {res.text[:300]}")


def test():
    url = SERVICES["rest_food"]
    total_all, _ = get(url, {"pageNo": 1, "numOfRows": 1})
    print(f"조건 없이 전체: {total_all}건\n")
    for value in ["탕후루", "%탕후루%"]:
        try:
            total, items = get(url, {"pageNo": 1, "numOfRows": 5,
                                     "cond[BPLC_NM::LIKE]": value})
            names = [i.get("BPLC_NM") for i in items]
            print(f"LIKE '{value}' → {total}건, 예시: {names}")
        except Exception as e:
            print(f"LIKE '{value}' → 오류: {e}")


def collect(like_value):
    for name, url in SERVICES.items():
        rows = []
        for item, words in KEYWORDS.items():
            for kw in words:
                value = like_value.format(kw=kw)
                print(f"[{name}] {kw} 요청 중...")
                total, items = get(url, {"pageNo": 1, "numOfRows": ROWS_PER_PAGE,
                                         "cond[BPLC_NM::LIKE]": value})
                pages = (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
                got = list(items)
                for page in range(2, pages + 1):
                    got.extend(get(url, {"pageNo": page, "numOfRows": ROWS_PER_PAGE,
                                         "cond[BPLC_NM::LIKE]": value})[1])
                    time.sleep(0.1)
                for r in got:
                    r["item"] = item
                rows.extend(got)
                print(f"[{name}] {kw}: 전국 {len(got)}건")

        df = pd.DataFrame(rows)
        if df.empty:
            print(f"[{name}] 결과 없음")
            continue
        df = df[[c for c in KEEP if c in df.columns] + ["item"]]
        df = df.drop_duplicates(subset=["MNG_NO", "item"])
        addr = df["ROAD_NM_ADDR"].fillna("") + " " + df["LOTNO_ADDR"].fillna("")
        df = df[addr.str.contains("|".join(SUDO))]
        df.to_csv(RAW / f"{name}_sudo.csv", index=False, encoding="utf-8-sig")
        print(f"저장: raw/{name}_sudo.csv (수도권 {len(df)}건)\n")


if __name__ == "__main__":
    collect("{kw}")