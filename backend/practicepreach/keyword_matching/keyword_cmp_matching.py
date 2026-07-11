from practicepreach.keyword_matching.keyword_extractors import *
import json
from collections import defaultdict, Counter



def import_manifesto_cmp(party: str, period: int):
    PERIOD_MAP = {
    20: "202109",
    21: "202502",
    }
    period_str = PERIOD_MAP[period]

    PROJECT_ROOT = Path(__file__).resolve().parents[1]  # practice-vs-preach/
    manifesto_path = PROJECT_ROOT / "data" / "german_manifestos" / f"{PARTY_CODE[party]}_{period_str}.json"
    print(party)
    print(PARTY_CODE[party])

    with open(manifesto_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data



def find_keywords_with_cmp_codes(data, keywords, party):
    results = []

    for item in data.get("items", []):
        text = item.get("text", "")
        text_lower = text.lower()
        cmp_code = item.get("cmp_code")

        for kw, weight in keywords:
            if kw.lower() in text_lower:
                results.append({
                    "party": party,
                    "keyword": kw,
                    "weight": float(weight),
                    "cmp_code": cmp_code,
                    "text": text
                })

    return results



def most_frequent_cmp_with_counts(matches):
    keyword_cmp_counts = defaultdict(Counter)

    for m in matches:
        keyword_cmp_counts[m["keyword"]][m["cmp_code"]] += 1

    result = {}
    for keyword, counter in keyword_cmp_counts.items():
        cmp_code, count = counter.most_common(1)[0]
        result[keyword] = {
            "cmp_code": cmp_code,
            "count": count,
            "distribution": dict(counter)
        }

    return result
