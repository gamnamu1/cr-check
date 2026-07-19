#!/usr/bin/env python3
"""
rq_postprocess_supplement.py — 2차 보완 지시의 1차 스냅샷 후처리 (일회성, 감리용).

API 재호출 없이 기존 스냅샷 7건(2026-07-18 캡처)을 후처리한다.

단계:
  C1) 구조 재정리 — 구 경로의 스냅샷을 candidates/<fixture_id>/<run_tag>.json 으로 이동.
      원본 삭제 전에 새 경로 사본의 sha256 동일성을 확인한다.
  B)  진단 덤프 매핑·아카이브 — backend/diagnostics/의 2026-07-18 덤프 7건을
      timestamp(0≤gen−dump≤30s)·내용(validated codes 일치, 첫 청크 preview 포함)으로
      스냅샷에 매핑, runs/diagnostics/<fid>/<run_tag>.json 으로 이동(사본 hash 검증 후 삭제).
      정확히 하나로 식별되지 않으면 unmatched/로 이동하고 사유 기록. 매핑표를 MAPPING.json에 저장.
  A)  스냅샷 필드 보강 — capture_validation(Task 1), semantic hash 9종(Task 5),
      diagnostic_path/sha256(Task 6), true_negative_candidate, postprocess 메타.
      원본 필드는 수정·삭제·이동·개명하지 않는다(새 필드 추가만) — 프로그램으로 불변성 검증.
  D)  기준(r1) 스냅샷 무결성 검증 — 필수 필드·규범 0건 여부·matched_text 실존
      (4단계 정규화 사다리, ' / ' 구분 다중 인용은 세그먼트별 검증).
      결과를 runs/matched_text_verification.json 에 저장. 실패는 DISCUSS로만 표시(교체·수정 없음).
  E)  selected/ 사본 생성 — 모든 후처리 완료 후, D를 통과한 표본만
      candidates/<fid>/r1.json → selected/<fid>.json 바이트 동일 복사(sha256 검증,
      report_input_sha256 필드 일치 확인).

주의: 이 스크립트는 스냅샷·문서 파일만 다룬다. DB 쓰기·API 호출 없음
      (Phase1 시스템 프롬프트 hash 계산을 위한 Supabase 읽기 전용 조회만 수행).
"""

import hashlib
import json
import sys
import unicodedata
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_quality_runner import (  # noqa: E402
    ROOT, RUNS_DIR, CANDIDATES_DIR, DIAG_ARCHIVE_DIR, DIAG_SRC_DIR,
    load_environment, _load_pipeline_modules,
    _sha256_text, compute_semantic_hashes, build_capture_validation,
)

SNAP_FLAT_DIR = RUNS_DIR / "snapshots"
SELECTED_DIR = SNAP_FLAT_DIR / "selected"
POSTPROCESS_VERSION = "rq_v1_supplement1"

OLD_FILES = {
    # 구 경로 파일명 → (fixture_id, run_tag)
    "PAST-DETENTION.json": ("PAST-DETENTION", "r1"),
    "PAST-DETENTION__r2.json": ("PAST-DETENTION", "r2"),
    "PAST-DETENTION__r3.json": ("PAST-DETENTION", "r3"),
    "E-12.json": ("E-12", "r1"),
    "E-12__r2.json": ("E-12", "r2"),
    "B-08.json": ("B-08", "r1"),
    "B-08__r2.json": ("B-08", "r2"),
}

BASELINE_FIXTURES = ["PAST-DETENTION", "E-12", "B-08", "C2-07"]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── C1: 구조 재정리 ────────────────────────────────────────────────────────
def stage_c1_move() -> list[dict]:
    moves = []
    for name, (fid, tag) in OLD_FILES.items():
        src = SNAP_FLAT_DIR / name
        if not src.exists():
            # 이미 이동됨(재실행 안전)
            continue
        dst_dir = CANDIDATES_DIR / fid
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{tag}.json"
        if dst.exists():
            raise RuntimeError(f"이동 대상이 이미 존재: {dst}")
        data = src.read_bytes()
        dst.write_bytes(data)
        src_sha, dst_sha = hashlib.sha256(data).hexdigest(), sha_file(dst)
        if src_sha != dst_sha:
            raise RuntimeError(f"이동 hash 불일치: {src} → {dst}")
        src.unlink()
        moves.append({"from": str(src.relative_to(ROOT)), "to": str(dst.relative_to(ROOT)),
                      "sha256": dst_sha, "verified": True})
    return moves


# ── B: 진단 덤프 매핑 ──────────────────────────────────────────────────────
def _task0_diag_names_by_sha() -> dict[str, str]:
    """Task 0 사전 보존 기록에서 sha256 → 원본 덤프 파일명 매핑을 복원한다."""
    p = ROOT / "docs/report-quality-recovery/audit/before-supplement/STATE_BEFORE_SUPPLEMENT.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    files = rec["gitignored_diagnostics_20260718_sha256"]["files"]
    return {v["sha256"]: k.split("/")[-1] for k, v in files.items()}


def _dump_matches_snapshot(dd: dict, sn: dict) -> tuple[bool, float]:
    ts = datetime.strptime(dd["timestamp"], "%Y%m%d_%H%M%S").replace(tzinfo=sn["gen"].tzinfo)
    delta = (sn["gen"] - ts).total_seconds()
    time_ok = 0 <= delta <= 30
    codes_ok = set(dd["checkpoint_3_pattern"]["validated_pattern_codes"]) == sn["codes"]
    preview = (dd["checkpoint_1_chunks"]["chunks_preview"] or [{}])[0].get("preview", "")
    content_ok = bool(preview) and preview[:40] in sn["article_text"]
    return time_ok and codes_ok and content_ok, delta


def stage_b_diag_mapping() -> dict:
    dumps = sorted(DIAG_SRC_DIR.glob("diagnostic_20260718_*.json"))
    name_by_sha = _task0_diag_names_by_sha()
    snaps = []
    for name, (fid, tag) in OLD_FILES.items():
        p = CANDIDATES_DIR / fid / f"{tag}.json"
        s = json.loads(p.read_text(encoding="utf-8"))
        snaps.append({"fid": fid, "tag": tag, "path": p,
                      "gen": datetime.fromisoformat(s["generated_at"]),
                      "codes": set(s["phase1"]["validated_pattern_codes"]),
                      "article_text": s["article"]["text"]})

    table, used_dumps = [], set()
    for sn in snaps:
        row = {"fixture_id": sn["fid"], "run_tag": sn["tag"]}
        # 재실행 안전: 이미 아카이브된 경우 아카이브 파일로 동일 기준을 재검증하고,
        # Task 0 사전 보존 hash로 원본 덤프 파일명·바이트 동일성을 복원한다.
        arch = DIAG_ARCHIVE_DIR / sn["fid"] / f"{sn['tag']}.json"
        if arch.exists():
            dd = json.loads(arch.read_text(encoding="utf-8"))
            ok, delta = _dump_matches_snapshot(dd, sn)
            arch_sha = sha_file(arch)
            orig_name = name_by_sha.get(arch_sha)
            if ok and orig_name:
                row.update({"dump": orig_name, "gen_minus_dump_seconds": round(delta, 1),
                            "criteria": "timestamp(0~30s)+validated_codes+first_chunk_preview",
                            "status": "matched",
                            "archived_to": str(arch.relative_to(ROOT)), "sha256": arch_sha,
                            "reverified_from_archive": True,
                            "task0_byte_identity": "사전 보존 sha256와 일치 — 원본과 바이트 동일"})
            else:
                row.update({"status": "unmatched",
                            "reason": f"아카이브 재검증 실패(criteria_ok={ok}, "
                                      f"task0_sha_match={orig_name is not None})"})
            table.append(row)
            continue
        matches = []
        for d in dumps:
            dd = json.loads(d.read_text(encoding="utf-8"))
            ok, delta = _dump_matches_snapshot(dd, sn)
            if ok:
                matches.append((d, delta))
        if len(matches) == 1:
            d, delta = matches[0]
            row.update({"dump": d.name, "gen_minus_dump_seconds": round(delta, 1),
                        "criteria": "timestamp(0~30s)+validated_codes+first_chunk_preview",
                        "status": "matched"})
            used_dumps.add(d.name)
        else:
            row.update({"status": "unmatched",
                        "reason": f"후보 {len(matches)}개 — 정확히 하나로 식별 불가"})
        table.append(row)

    # 이동 실행 — matched만; 나머지 7/18 덤프는 unmatched/로
    for row in table:
        if row["status"] != "matched":
            continue
        src = DIAG_SRC_DIR / row["dump"]
        if not src.exists():
            row["note"] = "이미 아카이브됨(재실행)"
            continue
        dst_dir = DIAG_ARCHIVE_DIR / row["fixture_id"]
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{row['run_tag']}.json"
        data = src.read_bytes()
        dst.write_bytes(data)
        if hashlib.sha256(data).hexdigest() != sha_file(dst):
            raise RuntimeError(f"진단 아카이브 hash 불일치: {src}")
        src.unlink()
        row["archived_to"] = str(dst.relative_to(ROOT))
        row["sha256"] = sha_file(dst)

    leftover = sorted(p.name for p in DIAG_SRC_DIR.glob("diagnostic_20260718_*.json"))
    unmatched_moved = []
    for name in leftover:
        src = DIAG_SRC_DIR / name
        um = DIAG_ARCHIVE_DIR / "unmatched"
        um.mkdir(parents=True, exist_ok=True)
        dst = um / name
        data = src.read_bytes()
        dst.write_bytes(data)
        if hashlib.sha256(data).hexdigest() != sha_file(dst):
            raise RuntimeError(f"unmatched 이동 hash 불일치: {src}")
        src.unlink()
        unmatched_moved.append(name)

    mapping = {
        "created": datetime.now().astimezone().isoformat(),
        "method": "dump.timestamp와 snapshot.generated_at의 차(0≤gen−dump≤30s) + "
                  "checkpoint_3 validated_pattern_codes 집합 일치 + "
                  "checkpoint_1 첫 청크 preview 40자가 기사 본문에 포함",
        "scope_note": "2026-07-18 생성 덤프(1차 표본 고정 실행분)만 대상. "
                      "그 이전 날짜의 덤프 237건은 과거 벤치마크·실험 세션 산출물로 이번 매핑 대상이 아니며 "
                      "backend/diagnostics/에 그대로 둔다. C2-07 r1·r2 덤프는 v2 runner가 capture 시점에 "
                      "자동 아카이브했다(runs/diagnostics/C2-07/).",
        "mappings": table,
        "unmatched_20260718_moved": unmatched_moved,
    }
    (DIAG_ARCHIVE_DIR / "MAPPING.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping


# ── A: 스냅샷 필드 보강 ────────────────────────────────────────────────────
def stage_a_postprocess(mapping: dict, phase1_prompt: str | None) -> list[dict]:
    diag_by_run = {(r["fixture_id"], r["run_tag"]): r for r in mapping["mappings"]}
    results = []
    for name, (fid, tag) in OLD_FILES.items():
        p = CANDIDATES_DIR / fid / f"{tag}.json"
        original = json.loads(p.read_text(encoding="utf-8"))
        if "capture_validation" in original:
            results.append({"file": str(p.relative_to(ROOT)), "note": "이미 후처리됨 — 건너뜀"})
            continue
        snap = deepcopy(original)

        detections = snap["phase1"]["detections"]
        codes = snap["phase1"]["validated_pattern_codes"]
        ethics_dicts = snap["ethics"]["refs"]
        forensic = snap["phase1"]["forensic"]

        cv = build_capture_validation(codes, ethics_dicts, forensic)
        if not cv["ethics_subset_of_validated"]:
            raise SystemExit(
                f"DISCUSS: [{fid}/{tag}] 규범 refs pattern_code가 validated 집합을 벗어남 — "
                f"{cv.get('subset_violation_codes')}")
        snap["capture_validation"] = cv
        snap["true_negative_candidate"] = len(codes) == 0

        hashes = compute_semantic_hashes(
            title=snap["article"]["title"],
            article_body=snap["article"]["text"],
            pattern_ids=snap["phase1"]["validated_pattern_ids"],
            detections=detections,
            overall_assessment=snap["phase1"]["overall_assessment"],
            article_context=snap["phase1"]["article_context"],
            ethics_dicts=ethics_dicts,
            validated_codes=codes,
            phase1_system_prompt=phase1_prompt,
        )
        snap.update(hashes)
        snap["semantic_hash_provenance"] = {
            "basis": "postprocess",
            "computed_at": datetime.now().astimezone().isoformat(),
            "code": "scripts/report_quality_runner.py compute_semantic_hashes() "
                    "(scripts/rq_postprocess_supplement.py에서 호출)",
            "phase1_prompt_note": (
                "phase1_system_prompt_sha256는 후처리 시점(2026-07-19)에 "
                "_build_sonnet_solo_prompt를 동일 커밋·동일 DB에서 재빌드해 계산 — "
                "캡처 시점(2026-07-18) 프롬프트 원문은 저장돼 있지 않으므로 "
                "그 사이 DB 혼동쌍이 불변이라는 가정 하의 값이다."
            ),
        }
        dg = diag_by_run.get((fid, tag), {})
        snap["diagnostic_path"] = dg.get("archived_to")
        snap["diagnostic_sha256"] = dg.get("sha256")
        snap["postprocess_version"] = POSTPROCESS_VERSION
        snap["postprocessed_at"] = datetime.now().astimezone().isoformat()

        # 원본 필드 불변성 검증 — 새 키 추가만 허용
        for k, v in original.items():
            if snap[k] != v:
                raise RuntimeError(f"원본 필드 변경 감지: {fid}/{tag} 키 {k}")
        added = sorted(set(snap) - set(original))
        p.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

        # 재현성 검증 — 파일을 다시 읽어 재계산
        s2 = json.loads(p.read_text(encoding="utf-8"))
        re_h = compute_semantic_hashes(
            title=s2["article"]["title"], article_body=s2["article"]["text"],
            pattern_ids=s2["phase1"]["validated_pattern_ids"],
            detections=s2["phase1"]["detections"],
            overall_assessment=s2["phase1"]["overall_assessment"],
            article_context=s2["phase1"]["article_context"],
            ethics_dicts=s2["ethics"]["refs"],
            validated_codes=s2["phase1"]["validated_pattern_codes"],
            phase1_system_prompt=phase1_prompt,
        )
        bad = [k for k, v in re_h.items() if s2.get(k) != v]
        if bad:
            raise RuntimeError(f"재현성 검증 실패 {fid}/{tag}: {bad}")
        results.append({"file": str(p.relative_to(ROOT)), "added_fields": added,
                        "file_sha256": sha_file(p)})
    return results


# ── D: matched_text 실존 검증 (4단계 사다리) ──────────────────────────────
_QUOTE_MAP = {
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    "\u201e": '"', "\u201f": '"', "\u2033": '"', "\u2032": "'",
}
_ELLIPSIS_RE = re.compile(r"[\u2026\u22ef\u2025]+|\.{2,}")
_QUOTE_STRIP_RE = re.compile(r"[\"'\u201c\u201d\u2018\u2019\u201e\u201f\u2032\u2033]")


def _norm2_nfkc(t: str) -> str:
    return unicodedata.normalize("NFKC", t)


def _norm3_ws(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def _norm4_punct(t: str) -> str:
    for k, v in _QUOTE_MAP.items():
        t = t.replace(k, v)
    return _ELLIPSIS_RE.sub("...", t)


def _find_stage(segment: str, haystack: str) -> str | None:
    """일치한 첫 단계 이름을 반환. 모두 실패하면 None."""
    if segment in haystack:
        return "stage1_exact"
    s, h = _norm2_nfkc(segment), _norm2_nfkc(haystack)
    if s in h:
        return "stage2_nfkc"
    s, h = _norm3_ws(s), _norm3_ws(h)
    if s in h:
        return "stage3_whitespace"
    s, h = _norm4_punct(s), _norm4_punct(h)
    if s in h:
        return "stage4_quotes_ellipsis"
    # 따옴표 정규화의 연장: 인용부호 자체를 양쪽에서 제거하고 비교.
    # Phase 1이 발췌 시 원문 내부의 인용부호를 탈락시키는 사례(B-08 3-2-b:
    # 원문 '…강화해야 한다"고 강조했다' → 추출 '…강화해야 한다고 강조했다') 대응.
    # 인용부호 외 문자는 완전 일치를 요구하므로 패러프레이즈는 통과할 수 없다.
    if _QUOTE_STRIP_RE.sub("", s) in _QUOTE_STRIP_RE.sub("", h):
        return "stage4_quotes_ellipsis_strip"
    return None


def stage_d_verify_baselines() -> dict:
    report = {"created": datetime.now().astimezone().isoformat(),
              "procedure": [
                  "1) 원문 그대로 exact substring",
                  "2) 양쪽 NFKC 정규화",
                  "3) 줄바꿈·연속 공백 → 단일 공백",
                  "4) 따옴표(곡선/일반 통일 → 최종적으로 인용부호 제거 비교)·말줄임표 표기 정규화 "
                  "— 인용부호 외 문자는 완전 일치 요구(패러프레이즈 통과 불가)",
                  "5) 그래도 불일치 → DISCUSS (환각 단정·r1 교체 없음)",
              ],
              "note_multi_quote": "Phase 1 프롬프트가 다중 인용을 ' / ' 구분 단일 문자열로 허용"
                                  "(pattern_matcher.py 650-654) — 세그먼트별로 검증한다. "
                                  "검색 공간은 제목+본문(제목 인용 패턴 대비).",
              "fixtures": {}}
    any_discuss = False
    for fid in BASELINE_FIXTURES:
        p = CANDIDATES_DIR / fid / "r1.json"
        s = json.loads(p.read_text(encoding="utf-8"))
        haystack = s["article"]["title"] + "\n\n" + s["article"]["text"]
        required_ok = all(k in s for k in (
            "snapshot_version", "fixture_id", "run_tag", "article", "phase1", "ethics",
            "capture_validation", "report_input_sha256", "stability_digest"))
        ethics_fail = (not s["true_negative_candidate"]) and s["ethics"]["count"] == 0
        rows = []
        for d in s["phase1"]["detections"]:
            segs = [x.strip() for x in d["matched_text"].split(" / ") if x.strip()]
            seg_rows = []
            for seg in segs:
                st = _find_stage(seg, haystack)
                seg_rows.append({"segment": seg[:60] + ("…" if len(seg) > 60 else ""),
                                 "matched_stage": st or "DISCUSS"})
                if st is None:
                    any_discuss = True
            rows.append({"pattern_code": d["pattern_code"], "segments": seg_rows,
                         "all_matched": all(r["matched_stage"] != "DISCUSS" for r in seg_rows)})
        fixture_ok = required_ok and not ethics_fail and all(r["all_matched"] for r in rows)
        report["fixtures"][fid] = {
            "file": str(p.relative_to(ROOT)),
            "required_fields_ok": required_ok,
            "ethics_zero_on_problem_article": ethics_fail,
            "detections": rows,
            "integrity_pass": fixture_ok,
        }
        if not fixture_ok:
            any_discuss = True
    report["any_discuss"] = any_discuss
    (RUNS_DIR / "matched_text_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


# ── E: selected/ 사본 생성 ────────────────────────────────────────────────
def stage_e_selected(verification: dict) -> list[dict]:
    SELECTED_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for fid in BASELINE_FIXTURES:
        v = verification["fixtures"][fid]
        if not v["integrity_pass"]:
            out.append({"fixture_id": fid, "status": "SKIPPED — 무결성 DISCUSS 미해결"})
            continue
        src = CANDIDATES_DIR / fid / "r1.json"
        dst = SELECTED_DIR / f"{fid}.json"
        data = src.read_bytes()
        dst.write_bytes(data)
        src_sha, dst_sha = hashlib.sha256(data).hexdigest(), sha_file(dst)
        if src_sha != dst_sha:
            raise RuntimeError(f"selected 사본 hash 불일치: {fid}")
        a = json.loads(src.read_text(encoding="utf-8"))
        b = json.loads(dst.read_text(encoding="utf-8"))
        if a["report_input_sha256"] != b["report_input_sha256"] or a != b:
            raise RuntimeError(f"selected 의미 내용 불일치: {fid}")
        out.append({"fixture_id": fid, "selected": str(dst.relative_to(ROOT)),
                    "file_sha256": dst_sha,
                    "report_input_sha256_match": True, "content_identical": True})
    return out


def main():
    print("== 환경 로드(읽기 전용 Supabase 조회용 — Anthropic 호출 없음) ==")
    load_environment(".env")
    mods = _load_pipeline_modules()
    sb_url, sb_key = mods.get_supabase_config()
    try:
        phase1_prompt = mods.pattern_matcher._build_sonnet_solo_prompt(sb_url, sb_key)
        print(f"phase1 prompt 빌드 OK — {len(phase1_prompt)}자, sha256 {_sha256_text(phase1_prompt)[:16]}…")
    except Exception as e:
        print(f"⚠️ phase1 prompt 빌드 실패 → hash null: {type(e).__name__}: {e}")
        phase1_prompt = None

    print("\n== C1: 구조 재정리(이동) ==")
    moves = stage_c1_move()
    print(json.dumps(moves, ensure_ascii=False, indent=1))

    print("\n== B: 진단 덤프 매핑·아카이브 ==")
    mapping = stage_b_diag_mapping()
    print(json.dumps(mapping["mappings"], ensure_ascii=False, indent=1))
    print("unmatched:", mapping["unmatched_20260718_moved"])

    print("\n== A: 스냅샷 필드 보강 ==")
    post = stage_a_postprocess(mapping, phase1_prompt)
    print(json.dumps(post, ensure_ascii=False, indent=1))

    print("\n== D: 기준(r1) 무결성·matched_text 검증 ==")
    ver = stage_d_verify_baselines()
    for fid, v in ver["fixtures"].items():
        flat = [seg for r in v["detections"] for seg in r["segments"]]
        stages = {}
        for seg in flat:
            stages[seg["matched_stage"]] = stages.get(seg["matched_stage"], 0) + 1
        print(f"  {fid}: integrity_pass={v['integrity_pass']} segments={stages}")
    print("any_discuss:", ver["any_discuss"])

    print("\n== E: selected/ 사본 ==")
    sel = stage_e_selected(ver)
    print(json.dumps(sel, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
