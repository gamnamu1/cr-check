#!/usr/bin/env python3
"""
M2 Seed SQL Generator for CR-Check Hybrid RAG DB.

Reads source data files and generates a Supabase migration SQL file
with INSERT statements for all seed data.

Input files:
  - docs/ethics_codes_mapping.json (394 ethics codes)
  - docs/current-criteria_v2_active.md (29+ patterns)
  - docs/golden_dataset_labels.json (pattern-ethics relations)

Output:
  - supabase/migrations/20260328100000_seed_data.sql
"""

import json
import re
from pathlib import Path


def escape_sql(text):
    """Escape single quotes for SQL string literals."""
    if text is None:
        return "NULL"
    return "'" + str(text).replace("'", "''") + "'"


def parse_patterns(criteria_path):
    """Parse patterns from current-criteria_v2_active.md."""
    content = criteria_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    categories = []  # 대분류
    patterns = []  # 소분류

    current_category = None
    current_pattern = None
    current_desc_lines = []

    for line in lines:
        # 대분류: ## **1-X. Name**
        cat_match = re.match(r'^## \*\*(\d+-\d+)\.\s+(.+?)\*\*', line)
        if cat_match:
            # Save previous pattern
            if current_pattern and current_desc_lines:
                current_pattern["description"] = "\n".join(current_desc_lines).strip()
                patterns.append(current_pattern)
                current_desc_lines = []
                current_pattern = None

            code = cat_match.group(1)
            name = cat_match.group(2).strip()
            current_category = {"code": code, "name": name}
            categories.append(current_category)
            continue

        # 소분류: ### **1-X-Y. Name**
        pat_match = re.match(r'^### \*\*(\d+-\d+-\d+)\.\s+(.+?)\*\*', line)
        if pat_match:
            # Save previous pattern
            if current_pattern and current_desc_lines:
                current_pattern["description"] = "\n".join(current_desc_lines).strip()
                patterns.append(current_pattern)
                current_desc_lines = []

            code = pat_match.group(1)
            name = pat_match.group(2).strip()
            # Determine parent category
            parent_code = "-".join(code.split("-")[:2])
            is_meta = code in ("1-4-1", "1-4-2")

            current_pattern = {
                "code": code,
                "name": name,
                "parent_code": parent_code,
                "category": next(
                    (c["name"] for c in categories if c["code"] == parent_code),
                    None,
                ),
                "subcategory": name,
                "is_meta_pattern": is_meta,
            }
            continue

        # Description lines (between ### headings)
        if current_pattern is not None:
            current_desc_lines.append(line)

    # Save last pattern
    if current_pattern and current_desc_lines:
        current_pattern["description"] = "\n".join(current_desc_lines).strip()
        patterns.append(current_pattern)

    # Add 1-7-2 manually (missing from criteria file, used in golden dataset)
    patterns.append(
        {
            "code": "1-7-2",
            "name": "헤드라인 윤리 문제",
            "parent_code": "1-7",
            "category": "언어와 표현의 윤리",
            "subcategory": "헤드라인 윤리 문제",
            "is_meta_pattern": False,
            "description": (
                "- **따옴표 저널리즘**: 취재원의 자극적 발언을 여과 없이 제목에 직접 인용하여 "
                "클릭을 유도하면서 보도 책임을 회피하는 행태.\n"
                "- **낚시성 제목**: 핵심 정보를 숨기고 호기심이나 불안감을 자극하는 제목으로 "
                "독자를 유인하는 행위. 말줄임표(…)나 '충격', '경악' 등의 자극적 표현 사용.\n"
                "- **제목-본문 불일치**: 제목이 암시하는 내용과 본문의 실제 내용이 심각하게 괴리되는 경우.\n"
                "- **편향적 프레이밍**: 특정 관점이나 가치판단이 내포된 제목으로 독자의 인식을 사전에 규정하는 행위."
            ),
        }
    )

    # Sort patterns by code
    patterns.sort(key=lambda p: [int(x) for x in p["code"].split("-")])

    return categories, patterns


def determine_non_citable_codes(ethics_data):
    """Determine which ethics codes should be is_citable=FALSE."""
    non_citable = set()

    for entry in ethics_data:
        code = entry["code"]
        # 서문/총강 (ends in -P, -T1, -T2)
        if code.endswith("-P") or code.endswith("-T1") or code.endswith("-T2"):
            non_citable.add(code)

    # 부칙/운영 조항
    non_citable.update(["DRG-40", "DRG-41", "DRG-42", "EPG-27", "EPG-28"])

    return non_citable


def extract_pattern_ethics_relations(labels_data):
    """Extract unique pattern-ethics relations from golden dataset labels."""
    relations = {}  # (pattern_code, ethics_code) -> (relation_type, strength, reasoning)

    # Mapping rules (approved)
    prefix_mapping = {
        "직접 적용": ("violates", "strong"),
        "보조 적용": ("related_to", "moderate"),
        "유추 적용": ("related_to", "weak"),
    }

    for label in labels_data.get("labels", []):
        if not label.get("expected_patterns"):
            continue  # Skip TN entries

        for pattern in label["expected_patterns"]:
            pattern_code = pattern["pattern_id"]
            for ethics in label.get("expected_ethics_codes", []):
                ethics_code = ethics["code"]
                rationale = ethics.get("rationale", "")

                # Determine mapping from rationale prefix
                mapped = None
                for prefix, (rel_type, strength) in prefix_mapping.items():
                    if rationale.startswith(prefix):
                        mapped = (rel_type, strength, rationale)
                        break

                if mapped is None:
                    continue  # Skip 상위 규범, 최상위 원칙

                key = (pattern_code, ethics_code)
                # Keep strongest relation if duplicate
                if key not in relations or (
                    mapped[1] == "strong" and relations[key][1] != "strong"
                ):
                    relations[key] = mapped

    return relations


def extract_pattern_cross_refs(patterns):
    """Extract pattern-to-pattern cross-references from descriptions."""
    refs = []
    seen = set()

    for pattern in patterns:
        desc = pattern.get("description", "")
        # Find references like (1-1-1), (1-3-2) in text
        matches = re.findall(r'\((\d+-\d+-\d+)\)', desc)
        for ref_code in matches:
            if ref_code != pattern["code"]:
                key = (pattern["code"], ref_code)
                if key not in seen:
                    seen.add(key)
                    refs.append(
                        {
                            "source": pattern["code"],
                            "target": ref_code,
                            "type": "variant_of",
                            "description": f"교차참조: {pattern['code']} → {ref_code}",
                        }
                    )

    # Meta pattern inferred_by relations
    meta_indicators = {
        "1-4-1": ["1-1-1", "1-1-2", "1-3-2"],
        "1-4-2": ["1-1-1", "1-7-3", "1-8-2"],
    }
    for meta_code, indicators in meta_indicators.items():
        for ind_code in indicators:
            key = (meta_code, ind_code)
            if key not in seen:
                seen.add(key)
                refs.append(
                    {
                        "source": meta_code,
                        "target": ind_code,
                        "type": "inferred_by",
                        "description": f"메타 패턴 관련 지표: {ind_code}",
                    }
                )

    return refs


def generate_sql(base_dir):
    """Generate the complete seed SQL migration."""
    # Read source files
    with open(base_dir / "docs/ethics_codes_mapping.json", encoding="utf-8") as f:
        ethics_data = json.load(f)

    with open(base_dir / "docs/golden_dataset_labels.json", encoding="utf-8") as f:
        labels_data = json.load(f)

    # Parse patterns
    criteria_path = base_dir / "docs/current-criteria_v2_active.md"
    categories, patterns = parse_patterns(criteria_path)

    # Determine is_citable
    non_citable = determine_non_citable_codes(ethics_data)

    # Extract relations
    pe_relations = extract_pattern_ethics_relations(labels_data)
    cross_refs = extract_pattern_cross_refs(patterns)

    # Extract junction data
    junctions = []
    for entry in ethics_data:
        if "junction" in entry:
            for junc in entry["junction"]:
                junctions.append(
                    {
                        "child_code": entry["code"],
                        "parent_code": junc["parent_code_id"],
                        "relation_note": junc.get("context_hint", ""),
                    }
                )

    sql = []

    # =============================================
    # Header
    # =============================================
    sql.append("-- ============================================")
    sql.append("-- CR-Check M2: Seed Data")
    sql.append("-- Migration: 20260328100000_seed_data")
    sql.append("--")
    sql.append(f"-- Ethics codes: {len(ethics_data)} entries (2-pass insertion)")
    sql.append(f"-- Patterns: {len(categories)} categories + {len(patterns)} items")
    sql.append(f"-- Junctions: {len(junctions)} entries")
    sql.append(f"-- Pattern-ethics relations: {len(pe_relations)} entries")
    sql.append(f"-- Pattern cross-refs: {len(cross_refs)} entries")
    sql.append(f"-- is_citable=FALSE: {len(non_citable)} entries")
    sql.append("-- ============================================")
    sql.append("")

    # =============================================
    # PASS 1: Ethics codes (parent_code_id = NULL)
    # =============================================
    sql.append("-- ============================================")
    sql.append("-- PASS 1: Ethics codes — parent_code_id = NULL")
    sql.append("-- ============================================")
    sql.append("")
    sql.append(
        "INSERT INTO public.ethics_codes "
        "(code, title, full_text, source, article_number, tier, "
        "tier_rationale, parent_code_id, domain, locale, "
        "version, is_active, effective_from, is_citable)"
    )
    sql.append("VALUES")

    values = []
    for entry in ethics_data:
        is_citable = "FALSE" if entry["code"] in non_citable else "TRUE"
        tier_rationale = escape_sql(entry.get("tier_rationale"))
        domain = escape_sql(entry.get("domain", "general"))

        val = (
            f"  ({escape_sql(entry['code'])}, {escape_sql(entry['title'])}, "
            f"{escape_sql(entry['full_text'])}, {escape_sql(entry['source'])}, "
            f"{escape_sql(entry.get('article_number'))}, {entry['tier']}, "
            f"{tier_rationale}, NULL, {domain}, 'ko-KR', "
            f"1, TRUE, '2026-03-15', {is_citable})"
        )
        values.append(val)

    sql.append(",\n".join(values) + ";")
    sql.append("")

    # =============================================
    # PASS 2: Update parent_code_id (code -> id mapping)
    # =============================================
    sql.append("-- ============================================")
    sql.append("-- PASS 2: Update parent_code_id (code → id)")
    sql.append("-- ============================================")
    sql.append("")

    parent_updates = []
    for entry in ethics_data:
        parent = entry.get("parent_code_id")
        if parent:
            parent_updates.append((entry["code"], parent))

    if parent_updates:
        sql.append(
            "UPDATE public.ethics_codes AS child\n"
            "SET parent_code_id = parent.id\n"
            "FROM public.ethics_codes AS parent\n"
            "WHERE parent.code = CASE child.code"
        )
        for child_code, parent_code in parent_updates:
            sql.append(f"  WHEN {escape_sql(child_code)} THEN {escape_sql(parent_code)}")
        sql.append("  END")
        sql.append(
            "AND child.code IN ("
            + ", ".join(escape_sql(c) for c, _ in parent_updates)
            + ");"
        )
    sql.append("")

    # =============================================
    # Ethics code hierarchy (junction table)
    # =============================================
    sql.append("-- ============================================")
    sql.append(f"-- Ethics code hierarchy (junction): {len(junctions)} entries")
    sql.append("-- ============================================")
    sql.append("")

    if junctions:
        sql.append(
            "INSERT INTO public.ethics_code_hierarchy "
            "(parent_code_id, child_code_id, relation_note)"
        )
        sql.append("SELECT p.id, c.id, v.relation_note")
        sql.append("FROM (VALUES")

        junc_values = []
        for j in junctions:
            junc_values.append(
                f"  ({escape_sql(j['parent_code'])}, {escape_sql(j['child_code'])}, "
                f"{escape_sql(j['relation_note'])})"
            )
        sql.append(",\n".join(junc_values))
        sql.append(") AS v(parent_code, child_code, relation_note)")
        sql.append(
            "JOIN public.ethics_codes p ON p.code = v.parent_code AND p.version = 1\n"
            "JOIN public.ethics_codes c ON c.code = v.child_code AND c.version = 1;"
        )
    sql.append("")

    # =============================================
    # Patterns: 대분류 (hierarchy_level = 1)
    # =============================================
    sql.append("-- ============================================")
    sql.append(f"-- Patterns 대분류: {len(categories)} entries")
    sql.append("-- ============================================")
    sql.append("")
    sql.append(
        "INSERT INTO public.patterns "
        "(code, name, description, category, hierarchy_level, "
        "is_meta_pattern, locale)"
    )
    sql.append("VALUES")

    cat_values = []
    for cat in categories:
        cat_values.append(
            f"  ({escape_sql(cat['code'])}, {escape_sql(cat['name'])}, "
            f"{escape_sql(cat['name'])}, {escape_sql(cat['name'])}, "
            f"1, FALSE, 'ko-KR')"
        )
    sql.append(",\n".join(cat_values) + ";")
    sql.append("")

    # =============================================
    # Patterns: 소분류 (hierarchy_level = 3)
    # =============================================
    sql.append("-- ============================================")
    sql.append(f"-- Patterns 소분류: {len(patterns)} entries")
    sql.append("-- ============================================")
    sql.append("")
    sql.append(
        "INSERT INTO public.patterns "
        "(code, name, description, category, subcategory, "
        "hierarchy_level, is_meta_pattern, locale)"
    )
    sql.append("VALUES")

    pat_values = []
    for p in patterns:
        desc = p.get("description", p["name"])
        is_meta = "TRUE" if p["is_meta_pattern"] else "FALSE"
        pat_values.append(
            f"  ({escape_sql(p['code'])}, {escape_sql(p['name'])}, "
            f"{escape_sql(desc)}, {escape_sql(p.get('category'))}, "
            f"{escape_sql(p.get('subcategory'))}, 3, {is_meta}, 'ko-KR')"
        )
    sql.append(",\n".join(pat_values) + ";")
    sql.append("")

    # Update parent_pattern_id for 소분류 → 대분류
    sql.append("-- Update parent_pattern_id (소분류 → 대분류)")
    sql.append(
        "UPDATE public.patterns AS child\n"
        "SET parent_pattern_id = parent.id\n"
        "FROM public.patterns AS parent\n"
        "WHERE parent.hierarchy_level = 1\n"
        "AND child.hierarchy_level = 3\n"
        "AND parent.code = LEFT(child.code, LENGTH(child.code) - "
        "LENGTH(SPLIT_PART(child.code, '-', 3)) - 1);"
    )
    sql.append("")

    # =============================================
    # Pattern-ethics relations
    # =============================================
    sql.append("-- ============================================")
    sql.append(f"-- Pattern-ethics relations: {len(pe_relations)} entries")
    sql.append("-- Mapping: 직접→violates/strong, 보조→related_to/moderate, 유추→related_to/weak")
    sql.append("-- ============================================")
    sql.append("")

    if pe_relations:
        sql.append(
            "INSERT INTO public.pattern_ethics_relations "
            "(pattern_id, ethics_code_id, relation_type, strength, reasoning)"
        )
        sql.append("SELECT p.id, ec.id, v.relation_type, v.strength, v.reasoning")
        sql.append("FROM (VALUES")

        rel_values = []
        for (pat_code, eth_code), (rel_type, strength, reasoning) in sorted(
            pe_relations.items()
        ):
            rel_values.append(
                f"  ({escape_sql(pat_code)}, {escape_sql(eth_code)}, "
                f"{escape_sql(rel_type)}, {escape_sql(strength)}, "
                f"{escape_sql(reasoning)})"
            )
        sql.append(",\n".join(rel_values))
        sql.append(") AS v(pattern_code, ethics_code, relation_type, strength, reasoning)")
        sql.append(
            "JOIN public.patterns p ON p.code = v.pattern_code\n"
            "JOIN public.ethics_codes ec ON ec.code = v.ethics_code AND ec.version = 1\n"
            "ON CONFLICT (pattern_id, ethics_code_id, relation_type) DO NOTHING;"
        )
    sql.append("")

    # =============================================
    # Pattern cross-references (pattern_relations)
    # =============================================
    sql.append("-- ============================================")
    sql.append(f"-- Pattern cross-references: {len(cross_refs)} entries")
    sql.append("-- ============================================")
    sql.append("")

    if cross_refs:
        sql.append(
            "INSERT INTO public.pattern_relations "
            "(source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified)"
        )
        sql.append("SELECT sp.id, tp.id, v.rel_type, v.desc_text, 'manual', 1.0, TRUE")
        sql.append("FROM (VALUES")

        xref_values = []
        for ref in cross_refs:
            xref_values.append(
                f"  ({escape_sql(ref['source'])}, {escape_sql(ref['target'])}, "
                f"{escape_sql(ref['type'])}, {escape_sql(ref['description'])})"
            )
        sql.append(",\n".join(xref_values))
        sql.append(") AS v(source_code, target_code, rel_type, desc_text)")
        sql.append(
            "JOIN public.patterns sp ON sp.code = v.source_code\n"
            "JOIN public.patterns tp ON tp.code = v.target_code\n"
            "ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;"
        )
    sql.append("")

    # =============================================
    # Summary comment
    # =============================================
    sql.append("-- ============================================")
    sql.append("-- Seed data summary:")
    sql.append(f"--   ethics_codes: {len(ethics_data)} records")
    sql.append(f"--   ethics_code_hierarchy: {len(junctions)} records")
    sql.append(f"--   patterns: {len(categories) + len(patterns)} records")
    sql.append(f"--   pattern_ethics_relations: {len(pe_relations)} records")
    sql.append(f"--   pattern_relations: {len(cross_refs)} records")
    sql.append(f"--   is_citable=FALSE: {sorted(non_citable)}")
    sql.append("-- ============================================")

    return "\n".join(sql)


def main():
    base_dir = Path(__file__).parent.parent
    sql = generate_sql(base_dir)

    output_path = base_dir / "supabase/migrations/20260328100000_seed_data.sql"
    output_path.write_text(sql, encoding="utf-8")

    print(f"Generated: {output_path}")
    print(f"  File size: {len(sql):,} bytes")
    print(f"  Lines: {sql.count(chr(10)) + 1:,}")


if __name__ == "__main__":
    main()
