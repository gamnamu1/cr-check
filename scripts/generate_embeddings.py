#!/usr/bin/env python3
"""
M3 Embedding Generator for CR-Check Hybrid RAG DB.

Generates OpenAI text-embedding-3-small vectors for patterns and ethics_codes,
then updates the local PostgreSQL database.

Usage:
    python scripts/generate_embeddings.py [--db-url URL]

Default DB: postgresql://postgres:postgres@127.0.0.1:54322/postgres
"""

import os
import sys
import time
import argparse
import re

import psycopg2
from openai import OpenAI
from dotenv import load_dotenv


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
SHORT_TEXT_THRESHOLD = 30
MAX_RETRIES = 3

# v3 leaf 코드 정규식 (예: 1-1-a, 6-2-c).
# SQL의 code ~ '^[0-9]+-[0-9]+-[a-z]+$' 와 의미 동일.
# Python 레이어 leaf 판정은 반드시 이 정규식을 사용 (hierarchy_level/is_meta_pattern 단독 판정 금지).
_LEAF_CODE_RE = re.compile(r'^[0-9]+-[0-9]+-[a-z]+$')


def _mask_db_url(url: str) -> str:
    """Redact password between user-info colon and '@' in postgres URL."""
    return re.sub(r'(://[^/:@]+):[^@]*@', r'\1:***@', url)


def connect_db(db_url):
    """Connect to PostgreSQL and return connection."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def fetch_patterns(conn):
    """Fetch embedding-target active vector leaf patterns.

    STEP 6 기준 (4개 필터):
    - is_active = TRUE
    - detection_strategy = 'vector'
    - code ~ '^[0-9]+-[0-9]+-[a-z]+$' (v3 leaf 정규식)
    description_embedding IS NULL 조건은 제거 — 직접 UPDATE 덮어쓰기 방식 (C-15).
    NULL/공백 search_text는 즉시 중단(sys.exit(1)) 처리.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, code, name, search_text, detection_strategy
            FROM public.patterns
            WHERE is_active = TRUE
              AND detection_strategy = 'vector'
              AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
            ORDER BY code
        """)
        rows = cur.fetchall()

    # NULL/공백 + leaf 정규식 외 코드 즉시 중단 (Python 레이어 이중 검증)
    for pid, code, name, search_text, detection_strategy in rows:
        if not search_text or not search_text.strip():
            print(f"ERROR: search_text 결함: {code} — 즉시 중단")
            sys.exit(1)
        if not _LEAF_CODE_RE.match(code):
            print(f"ERROR: leaf 정규식 외 코드: {code} — 즉시 중단")
            sys.exit(1)

    return rows


def fetch_ethics_codes(conn):
    """Fetch embedding-target ethics codes (citable + active)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, code, title, full_text, length(full_text) AS text_len
            FROM ethics_codes
            WHERE is_citable = TRUE AND is_active = TRUE
              AND text_embedding IS NULL
            ORDER BY code
        """)
        return cur.fetchall()


def prepare_texts(patterns, ethics_codes):
    """Prepare embedding texts, handling short entries.

    STEP 6: patterns 임베딩 입력은 search_text 단독.
            description은 리포트용 필드로 보존하며 임베딩에 사용하지 않는다 (C-13).
    """
    items = []  # [(table, id, code, text)]
    short_entries = []

    # Patterns: search_text 단독 사용. NULL/공백은 fetch_patterns()에서 이미 차단됨 (중복 검사 금지)
    for row in patterns:
        pid, code, name, search_text, detection_strategy = row
        items.append(("patterns", pid, code, search_text.strip()))

    # Ethics codes: handle short texts
    for row in ethics_codes:
        eid, code, title, full_text, text_len = row
        if text_len < SHORT_TEXT_THRESHOLD:
            combined = f"{title} — {full_text}"
            items.append(("ethics_codes", eid, code, combined))
            short_entries.append((code, title, text_len))
        else:
            items.append(("ethics_codes", eid, code, full_text))

    return items, short_entries


def call_openai_embeddings(client, texts, model=EMBEDDING_MODEL):
    """Call OpenAI embeddings API with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def update_embeddings(conn, table, id_embedding_pairs, column):
    """Batch UPDATE embeddings into the database."""
    updated = 0
    failed = []

    with conn.cursor() as cur:
        for record_id, embedding in id_embedding_pairs:
            try:
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
                cur.execute(
                    f"UPDATE {table} SET {column} = %s::vector WHERE id = %s",
                    (embedding_str, record_id),
                )
                updated += 1
            except Exception as e:
                conn.rollback()
                failed.append((record_id, str(e)))

    conn.commit()
    return updated, failed


def verify_embeddings(conn):
    """Verify embedding counts and dimensions.

    STEP 6 patterns 필터 (전면 교체, 보충 지시):
    - is_active = TRUE
    - detection_strategy = 'vector'
    - code ~ '^[0-9]+-[0-9]+-[a-z]+$'
    기존 is_meta_pattern=FALSE / hierarchy_level=3 단독 조건은 사용하지 않는다.
    pattern_dims는 DISTINCT로 모든 차원을 리스트로 수집 — 정상 시 정확히 [1536].
    """
    results = {}
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*) FROM patterns
            WHERE is_active = TRUE
              AND detection_strategy = 'vector'
              AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
        """)
        results["patterns_target"] = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*) FROM ethics_codes
            WHERE is_citable = TRUE AND is_active = TRUE
        """)
        results["ethics_target"] = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*) FROM patterns
            WHERE is_active = TRUE
              AND detection_strategy = 'vector'
              AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
              AND description_embedding IS NOT NULL
        """)
        results["patterns_with_embedding"] = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*) FROM ethics_codes
            WHERE is_citable = TRUE AND is_active = TRUE
              AND text_embedding IS NOT NULL
        """)
        results["ethics_with_embedding"] = cur.fetchone()[0]

        cur.execute("""
            SELECT DISTINCT vector_dims(description_embedding)
            FROM patterns
            WHERE is_active = TRUE
              AND detection_strategy = 'vector'
              AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
              AND description_embedding IS NOT NULL
        """)
        results["pattern_dims"] = [row[0] for row in cur.fetchall()]

        cur.execute("""
            SELECT vector_dims(text_embedding)
            FROM ethics_codes
            WHERE text_embedding IS NOT NULL LIMIT 1
        """)
        row = cur.fetchone()
        results["ethics_dims"] = row[0] if row else None

    return results


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for CR-Check DB")
    parser.add_argument(
        "--db-url",
        default="postgresql://postgres:postgres@127.0.0.1:54322/postgres",
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--patterns-only",
        action="store_true",
        help="Process only patterns table (skip ethics_codes). STEP 6 mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show fetch result without OpenAI/UPDATE. Must be used with --patterns-only.",
    )
    args = parser.parse_args()

    # STEP 6 강제 가드: --dry-run 단독 실행 차단 (코드 레벨)
    if args.dry_run and not args.patterns_only:
        print("ERROR: --dry-run must be used with --patterns-only in STEP 6")
        sys.exit(1)

    if args.patterns_only:
        print(f"--- Mode: patterns-only{' (DRY RUN)' if args.dry_run else ''} ---")

    # Load environment
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    # Connect to DB
    print(f"Connecting to: {_mask_db_url(args.db_url)}")
    conn = connect_db(args.db_url)

    # OpenAI client는 dry-run이 아닐 때만 생성 (C-11)
    client = None
    if not args.dry_run:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in environment")
            sys.exit(1)
        client = OpenAI(api_key=api_key)

    # Fetch data
    print("\n--- Fetching embedding targets ---")
    patterns = fetch_patterns(conn)
    if args.patterns_only:
        ethics_codes = []
    else:
        ethics_codes = fetch_ethics_codes(conn)
    print(f"  Patterns (active vector leaf): {len(patterns)}")
    print(f"  Ethics codes (citable, active): {len(ethics_codes)}")

    # 0건 가드 (STEP 6 진입 조건 미충족 시 즉시 중단, dry-run 포함)
    if args.patterns_only and len(patterns) == 0:
        print("ERROR: 0건. STEP 6 진입 조건 미충족 — 즉시 중단")
        sys.exit(1)

    # Dry-run 종료점: fetch 결과 출력 후 즉시 종료. OpenAI 호출/UPDATE/verify 모두 skip.
    if args.dry_run:
        print("\n--- Dry-run target codes ---")
        for pid, code, name, search_text, detection_strategy in patterns:
            preview = (search_text[:60] + "...") if len(search_text) > 60 else search_text
            print(f"  [{code}] {name}  | search_text({len(search_text)}자): {preview}")
        print(f"\n✓ Dry-run complete. {len(patterns)} patterns ready for embedding.")
        conn.close()
        return

    # Prepare texts
    items, short_entries = prepare_texts(patterns, ethics_codes)
    total = len(items)
    print(f"  Total embedding targets: {total}")

    # Report short entries
    if short_entries:
        print(f"\n--- Short text entries ({len(short_entries)} items, < {SHORT_TEXT_THRESHOLD} chars) ---")
        print(f"  These use 'title — full_text' combined text for embedding:")
        for code, title, text_len in short_entries:
            print(f"    {code} ({text_len}자): {title}")

    # Estimate cost
    avg_tokens_per_text = 350
    estimated_tokens = total * avg_tokens_per_text
    estimated_cost = estimated_tokens * 0.02 / 1_000_000
    print(f"\n--- Cost estimate ---")
    print(f"  ~{estimated_tokens:,} tokens × $0.02/1M = ~${estimated_cost:.4f}")

    # Generate embeddings
    print(f"\n--- Generating embeddings ({EMBEDDING_MODEL}) ---")
    texts = [item[3] for item in items]

    # Split into chunks of 2048 (API limit)
    chunk_size = 2048
    all_embeddings = []
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i : i + chunk_size]
        print(f"  API call: {len(chunk)} texts (batch {i // chunk_size + 1})...")
        embeddings = call_openai_embeddings(client, chunk)
        all_embeddings.extend(embeddings)
        print(f"  Received {len(embeddings)} embeddings")

    # Map embeddings back to items
    pattern_updates = []
    ethics_updates = []
    for idx, item in enumerate(items):
        table, record_id, code, text = item
        if table == "patterns":
            pattern_updates.append((record_id, all_embeddings[idx]))
        else:
            ethics_updates.append((record_id, all_embeddings[idx]))

    # Update DB
    print(f"\n--- Updating database ---")
    p_ok, p_fail = update_embeddings(conn, "patterns", pattern_updates, "description_embedding")
    print(f"  Patterns: {p_ok}/{len(pattern_updates)} updated")
    if p_fail:
        print(f"  Pattern failures: {p_fail}")

    # patterns-only 모드: ethics_codes UPDATE 호출 자체를 skip (C-11)
    if args.patterns_only:
        e_ok = 0
        e_fail = []
    else:
        e_ok, e_fail = update_embeddings(conn, "ethics_codes", ethics_updates, "text_embedding")
        print(f"  Ethics codes: {e_ok}/{len(ethics_updates)} updated")
        if e_fail:
            print(f"  Ethics failures: {e_fail}")

    # Verify
    print(f"\n--- Verification ---")
    v = verify_embeddings(conn)
    print(f"  Patterns with embedding: {v['patterns_with_embedding']}/{v['patterns_target']}")
    if not args.patterns_only:
        print(f"  Ethics codes with embedding: {v['ethics_with_embedding']}/{v['ethics_target']}")
    print(f"  Pattern embedding dims: {v['pattern_dims']}")
    if not args.patterns_only:
        print(f"  Ethics embedding dims: {v['ethics_dims']}")

    # all_ok 판정: pattern_dims는 DISTINCT 차원 리스트. 정상 시 정확히 [1536].
    # patterns-only 모드에서는 ethics 관련 조건과 e_fail 제외 (C-11 + C-14 보충).
    if args.patterns_only:
        all_ok = (
            v["patterns_with_embedding"] == v["patterns_target"]
            and v["pattern_dims"] == [EMBEDDING_DIM]
            and not p_fail
        )
    else:
        all_ok = (
            v["patterns_with_embedding"] == v["patterns_target"]
            and v["ethics_with_embedding"] == v["ethics_target"]
            and v["pattern_dims"] == [EMBEDDING_DIM]
            and v["ethics_dims"] == EMBEDDING_DIM
            and not p_fail
            and not e_fail
        )

    if all_ok:
        print(f"\n✓ All {total} embeddings generated and stored successfully.")
    else:
        print(f"\n✗ Some embeddings failed. Check logs above.")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
