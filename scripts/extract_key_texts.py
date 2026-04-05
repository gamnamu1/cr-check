#!/usr/bin/env python3
"""
Extract article_key_text from golden dataset articles using GPT-4o.

Reads article texts, extracts ethically problematic key sentences,
and updates golden_dataset_final.json with article_key_text field.
"""

import json
import os
import shutil
import sys
import time

from openai import OpenAI
from dotenv import load_dotenv

ARTICLE_TEXTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "Golden_Data_Set_Pool", "article_texts"
)
TN_IDS = {"C-02", "C-04", "C2-01", "C2-07", "E-17", "E-19"}

EXTRACTION_PROMPT = """아래 뉴스 기사에서 저널리즘 윤리 위반이 의심되는 핵심 문장 또는 표현을
2~3개 추출해줘. 각 문장은 원문 그대로 인용하되,
왜 윤리적으로 문제가 될 수 있는지 간단히 이유를 덧붙여줘.

추출 기준:
- 사실 검증 없이 단정하는 표현
- 한쪽 시각만 반영한 편향적 서술
- 선정적이거나 갈등을 조장하는 프레이밍
- 인권 침해적 표현 (피해자 신원 노출, 차별적 표현 등)
- 출처 불명확한 정보 인용
- 기타 저널리즘 윤리 강령에 어긋나는 표현

출력 형식 (JSON만 출력, 다른 텍스트 없이):
{
  "key_sentences": [
    {
      "sentence": "원문에서 추출한 문장",
      "reason": "윤리적 문제가 되는 이유"
    }
  ]
}

기사 원문:
"""


def load_article(candidate_id):
    """Load article text file."""
    path = os.path.join(ARTICLE_TEXTS_DIR, f"{candidate_id}_article.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return None


def extract_key_sentences(client, article_text):
    """Use GPT-4o to extract key sentences."""
    # Truncate very long articles
    text = article_text[:6000]

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": EXTRACTION_PROMPT + text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("key_sentences", [])
        except Exception as e:
            if attempt < 2:
                print(f"    Retry ({attempt + 1}/3): {e}")
                time.sleep(2 ** attempt)
            else:
                print(f"    FAILED: {e}")
                return []


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    base_dir = os.path.join(os.path.dirname(__file__), "..")

    # Load golden dataset
    gd_path = os.path.join(base_dir, "docs", "golden_dataset_final.json")
    with open(gd_path, encoding="utf-8") as f:
        gd = json.load(f)

    # Backup original
    backup_path = os.path.join(base_dir, "docs", "golden_dataset_final_backup.json")
    shutil.copy2(gd_path, backup_path)
    print(f"Backup saved: {backup_path}")

    # Load labels for reference
    with open(os.path.join(base_dir, "docs", "golden_dataset_labels.json"), encoding="utf-8") as f:
        labels = json.load(f)
    label_map = {l["candidate_id"]: l for l in labels["labels"]}

    # Process each candidate
    total_sentences = 0
    total_lengths = []

    print(f"\n{'='*70}")
    print(f"Extracting article_key_text for {len(gd['candidates'])} candidates")
    print(f"{'='*70}\n")

    for candidate in gd["candidates"]:
        cid = candidate["candidate_id"]

        if cid in TN_IDS:
            candidate["article_key_text"] = ""
            print(f"[{cid}] TN — article_key_text = '' (빈 문자열)")
            continue

        article_text = load_article(cid)
        if not article_text:
            print(f"[{cid}] WARNING: article text not found")
            candidate["article_key_text"] = ""
            continue

        # Get expected patterns for display
        label = label_map.get(cid, {})
        expected = [p["pattern_id"] for p in label.get("expected_patterns", [])]

        print(f"[{cid}] Expected: {expected}")
        print(f"  Article length: {len(article_text)} chars")

        # Extract key sentences
        sentences = extract_key_sentences(client, article_text)

        if sentences:
            # Join sentences only (no reasons) with newline
            key_text = "\n".join(s["sentence"] for s in sentences)
            candidate["article_key_text"] = key_text

            for s in sentences:
                print(f"  → \"{s['sentence'][:80]}...\"")
                print(f"    이유: {s['reason'][:60]}")
                total_lengths.append(len(s["sentence"]))

            total_sentences += len(sentences)
        else:
            candidate["article_key_text"] = ""
            print(f"  → 추출 실패")

        print()

    # Save updated golden dataset
    with open(gd_path, "w", encoding="utf-8") as f:
        json.dump(gd, f, ensure_ascii=False, indent=2)

    print(f"{'='*70}")
    print(f"추출 완료 요약")
    print(f"{'='*70}")
    print(f"  총 추출 문장: {total_sentences}건")
    print(f"  평균 문장 길이: {sum(total_lengths)/len(total_lengths):.0f}자" if total_lengths else "  평균 문장 길이: N/A")
    print(f"  golden_dataset_final.json 업데이트 완료")
    print(f"  원본 백업: {backup_path}")


if __name__ == "__main__":
    main()
