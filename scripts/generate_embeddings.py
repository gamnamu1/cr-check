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


def _mask_db_url(url: str) -> str:
    """Redact password between user-info colon and '@' in postgres URL."""
    return re.sub(r'(://[^/:@]+):[^@]*@', r'\1:***@', url)


def connect_db(db_url):
    """Connect to PostgreSQL and return connection."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def fetch_patterns(conn):
    """Fetch embedding-target patterns (non-meta, 소분류 only)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, code, description
            FROM patterns
            WHERE is_meta_pattern = FALSE AND hierarchy_level = 3
              AND description_embedding IS NULL
            ORDER BY code
        """)
        return cur.fetchall()


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
    """Prepare embedding texts, handling short entries."""
    items = []  # [(table, id, code, text)]
    short_entries = []

    # Patterns: use description
    for row in patterns:
        pid, code, description = row
        items.append(("patterns", pid, code, description))

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
    """Verify embedding counts and dimensions."""
    results = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM patterns WHERE description_embedding IS NOT NULL"
        )
        results["patterns_with_embedding"] = cur.fetchone()[0]

        cur.execute(
            "SELECT count(*) FROM ethics_codes WHERE text_embedding IS NOT NULL"
        )
        results["ethics_with_embedding"] = cur.fetchone()[0]

        cur.execute("""
            SELECT vector_dims(description_embedding)
            FROM patterns
            WHERE description_embedding IS NOT NULL LIMIT 1
        """)
        row = cur.fetchone()
        results["pattern_dims"] = row[0] if row else None

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
    args = parser.parse_args()

    # Load environment
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Connect to DB
    print(f"Connecting to: {_mask_db_url(args.db_url)}")
    conn = connect_db(args.db_url)

    # Fetch data
    print("\n--- Fetching embedding targets ---")
    patterns = fetch_patterns(conn)
    ethics_codes = fetch_ethics_codes(conn)
    print(f"  Patterns (non-meta, 소분류): {len(patterns)}")
    print(f"  Ethics codes (citable, active): {len(ethics_codes)}")

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

    e_ok, e_fail = update_embeddings(conn, "ethics_codes", ethics_updates, "text_embedding")
    print(f"  Ethics codes: {e_ok}/{len(ethics_updates)} updated")
    if e_fail:
        print(f"  Ethics failures: {e_fail}")

    # Verify
    print(f"\n--- Verification ---")
    v = verify_embeddings(conn)
    print(f"  Patterns with embedding: {v['patterns_with_embedding']}/28")
    print(f"  Ethics codes with embedding: {v['ethics_with_embedding']}/373")
    print(f"  Pattern embedding dims: {v['pattern_dims']}")
    print(f"  Ethics embedding dims: {v['ethics_dims']}")

    all_ok = (
        v["patterns_with_embedding"] == len(pattern_updates)
        and v["ethics_with_embedding"] == len(ethics_updates)
        and v["pattern_dims"] == EMBEDDING_DIM
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
