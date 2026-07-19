#!/usr/bin/env python3
"""
report_quality_runner.py — 리포트 품질 진단용 표본 고정 러너 (v2, 2차 보완 반영).

목적:
  docs/report-quality-recovery/fixtures/fixtures.json 에 고정된 표본 기사에 대해
  현재 파이프라인의 Phase 1 탐지 결과 + 그 시점의 윤리규범 조회 결과를
  재현 가능한 스냅샷 JSON으로 저장한다.

원칙:
  - core.pipeline.analyze_article 를 직접 import 해 호출한다.
    운영 API(backend/main.py /analyze)·URL 캐시(get_cached_analysis)·
    DB 저장(save_analysis_result)은 일절 경유하지 않는다.
  - run_sonnet=False 로 호출한다. Phase 2 리포트 생성은 이 스크립트의 범위가 아니다.
  - 윤리규범은 fetch_ethics_for_patterns()를 별도 호출해 스냅샷에 포함한다(읽기 전용 RPC).
    호출 인자는 generate_report() 내부 호출(report_generator.py 803-808)과 동일하게 맞춘다.
  - DB에 대한 쓰기·삭제·마이그레이션은 수행하지 않는다.

v2 변경(2차 보완 지시):
  - Task 1: capture_validation 필드 — run_sonnet=False에서 forensic.patterns_without_ethics가
    validated 전체로 채워지는 문제(pipeline.py 341-343)를 별도 조회 규범 기준으로 재계산해 기록.
    + 부분집합 assertion(규범 매핑 패턴 ⊆ validated 패턴).
  - Task 5: semantic hash 9종을 capture 시점에 기록.
  - Task 6: backend/diagnostics/ 진단 덤프를 실행 전후 diff로 자동 아카이브.
  - Task 7: API 키 로딩을 명시적으로 — 묵시적 override 제거, placeholder 감지 시 명시적 실패,
    키 내용은 어떤 형태로도 출력하지 않음(존재 여부·길이·출처까지만).
  - Task 3: 스냅샷을 candidates/<fixture_id>/<run_tag>.json 구조로 저장.

사용:
  python scripts/report_quality_runner.py --ids C2-07 --run-tag r1
  python scripts/report_quality_runner.py --ids C2-07 --run-tag r2
  python scripts/report_quality_runner.py --ids C2-07 --env-file .env   # 셸 키가 placeholder일 때 명시적 우선

저장 위치:
  docs/report-quality-recovery/runs/snapshots/candidates/<fixture_id>/<run_tag>.json
  docs/report-quality-recovery/runs/diagnostics/<fixture_id>/<run_tag>.json (파이프라인 진단 덤프)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent

FIXTURES_PATH = ROOT / "docs" / "report-quality-recovery" / "fixtures" / "fixtures.json"
RUNS_DIR = ROOT / "docs" / "report-quality-recovery" / "runs"
CANDIDATES_DIR = RUNS_DIR / "snapshots" / "candidates"
DIAG_ARCHIVE_DIR = RUNS_DIR / "diagnostics"
DIAG_SRC_DIR = ROOT / "backend" / "diagnostics"

ENTRYPOINT_NOTE = (
    "core.pipeline.analyze_article 직접 호출 — 운영 API(/analyze), "
    "URL 캐시(get_cached_analysis), DB 저장(save_analysis_result) 미경유"
)

SNAPSHOT_VERSION = "rq_v2"

# ── Task 7: API 키 로딩·로깅 ───────────────────────────────────────────────
# 실제 키 길이: ANTHROPIC 100+자, OPENAI 50+자. 셸에서 발견된 placeholder는 10자("...").
# 검증 기준은 보수적으로 40자 미만 또는 리터럴 "..." 포함이면 placeholder로 본다.
_REQUIRED_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
_MIN_KEY_LENGTH = 40


def _key_is_valid(value: str) -> bool:
    return bool(value) and len(value) >= _MIN_KEY_LENGTH and "..." not in value


def load_environment(env_file: str | None) -> dict:
    """API 키를 명시적으로 로드·검증한다.

    - 기본: load_dotenv(ROOT/.env)를 override 없이 호출한다(기존 env 유지 — python-dotenv 기본).
      셸 변수가 placeholder면 조용히 뒤집지 않고 아래 검증에서 명시적으로 실패한다.
    - --env-file 지정 시에만 해당 파일을 override=True로 우선한다(사용자의 명시적 지시).
    - 로그에는 키의 존재 여부·길이·출처(shell/env file)까지만 남긴다.
      키 내용(앞부분·뒷부분 포함)은 어떤 형태로도 출력하지 않는다.
    """
    from dotenv import load_dotenv, dotenv_values

    shell_state = {
        name: {"shell_present": name in os.environ, "shell_length": len(os.environ.get(name, ""))}
        for name in _REQUIRED_KEYS
    }

    if env_file:
        env_path = Path(env_file)
        if not env_path.is_absolute():
            env_path = ROOT / env_path
        if not env_path.exists():
            raise SystemExit(f"--env-file 경로가 존재하지 않습니다: {env_path}")
        load_dotenv(env_path, override=True)
        load_mode = f"--env-file {env_path.name} (명시적 우선, override=True)"
    else:
        env_path = ROOT / ".env"
        load_dotenv(env_path)  # override 없음 — 셸 env를 조용히 뒤집지 않는다
        load_mode = ".env (override 없음 — 셸 env 우선 유지)"

    file_values = dotenv_values(env_path)
    report = {"load_mode": load_mode, "keys": {}}
    invalid: list[str] = []
    for name in _REQUIRED_KEYS:
        final = os.environ.get(name, "")
        if final and final == (file_values.get(name) or ""):
            source = "env file"
        elif shell_state[name]["shell_present"]:
            source = "shell"
        else:
            source = "absent"
        entry = {
            **shell_state[name],
            "final_length": len(final),
            "source": source,
            "valid": _key_is_valid(final),
        }
        report["keys"][name] = entry
        print(
            f"  [env] {name}: present={bool(final)}, length={len(final)}, source={source}"
        )
        if not entry["valid"]:
            invalid.append(name)

    if invalid:
        lines = [
            f"유효하지 않은 API 키 감지: {', '.join(invalid)} "
            f"(길이 {_MIN_KEY_LENGTH}자 미만 또는 placeholder 형식).",
            "원인: 셸 환경에 자리표시자 키가 export되어 있으면 load_dotenv 기본 동작은",
            "      기존 env를 덮어쓰지 않으므로 .env의 실제 키가 무시됩니다.",
            "해결: (1) 셸에서 `unset <키 이름>` 후 재실행하거나 셸 rc에서 자리표시자 export를 제거,",
            "      (2) 또는 `--env-file .env` 옵션으로 파일 우선을 명시적으로 지시하세요.",
        ]
        raise SystemExit("\n".join(lines))
    return report


def _load_pipeline_modules() -> SimpleNamespace:
    """환경 검증 이후에만 파이프라인 모듈을 import한다(임포트 시점 부작용 차단)."""
    backend = str(ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from core.pipeline import analyze_article, _build_haiku_dicts  # noqa: E402
    from core import pattern_matcher  # noqa: E402
    from core.report_generator import fetch_ethics_for_patterns  # noqa: E402
    from core.db import _get_supabase_config  # noqa: E402

    return SimpleNamespace(
        analyze_article=analyze_article,
        build_haiku_dicts=_build_haiku_dicts,
        pattern_matcher=pattern_matcher,
        fetch_ethics_for_patterns=fetch_ethics_for_patterns,
        get_supabase_config=_get_supabase_config,
    )


# ── 공용 해시 유틸 ─────────────────────────────────────────────────────────
def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_dumps(obj) -> str:
    """canonical JSON 직렬화 — dict 키는 사전순 고정(sort_keys), 리스트 순서는 주어진 그대로,
    구분자 고정(separators), 비ASCII 원문 유지(ensure_ascii=False)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_canonical(obj) -> str:
    return _sha256_text(_canonical_dumps(obj))


def _stability_digest(codes: list[str], detections: list[dict]) -> str:
    """반복 실행 비교용 요약 해시 — (pattern_code, severity) 정렬 쌍 기준."""
    pairs = sorted((d.get("pattern_code", ""), d.get("severity", "")) for d in detections)
    payload = json.dumps({"codes": sorted(codes), "pairs": pairs}, ensure_ascii=False)
    return _sha256_text(payload)


def compute_semantic_hashes(
    *,
    title: str,
    article_body: str,
    pattern_ids: list,
    detections: list[dict],
    overall_assessment: str,
    article_context: str,
    ethics_dicts: list[dict],
    validated_codes: list[str],
    phase1_system_prompt: str | None,
) -> dict:
    """Task 5 — semantic hash 9종.

    - analysis_input_sha256: Phase 1 입력 요소의 hash. 단순 문자열 결합이 아니라
      canonical JSON {"article_text": <본문>, "title": <제목>} (sort_keys로 키 순서 고정)로
      계산한다. 실제 Phase 1 전달값 기준: analyze_article(article_text=본문, title=제목)
      — pipeline.py 173-209.
    - detections_canonical_sha256: 탐지 목록을 항목별 canonical 직렬화 문자열 기준으로
      정렬한 뒤 canonical JSON으로 계산(순서 무관 의미 동일성).
    - detections_ordered_sha256: 저장 순서 그대로 canonical JSON으로 계산(순서 포함).
    - ethics_snapshot_sha256: 규범 목록을 정렬 후 canonical JSON으로 계산 —
      목적: 규범 집합의 의미 동일성 확인(순서 무관).
    - report_input_sha256: 이후 리포트 생성 단계에 실제로 전달될 입력 전체의 동일성 확인
      (순서 포함). 현재 코드의 generate_report() 호출(pipeline.py 248-255)에 실제로
      전달되는 인자만으로 계산한다:
        포함 — article_text(전달 실제값=본문), pattern_ids(전달 순서 유지),
               detections(전달 순서 유지), overall_assessment,
               meta_patterns(실제 전달값: 메타패턴 비활성화로 빈 리스트 [] — pipeline.py 223·253),
               article_context, ethics_refs(fetch_ethics_for_patterns 반환 순서 유지 —
               generate_report 내부 조회와 동일 인자·동일 함수, EthicsReference asdict 직렬화)
        제목 — generate_report 시그니처(report_generator.py 783-790)에 title 인자가 없고
               pipeline도 전달하지 않으므로 제외한다. 제목 동일성은
               article_title_sha256·analysis_input_sha256이 담당한다.
        제외 — 모든 hash 필드, generated_at, timing, run_tag, diagnostic 참조,
               file_sha256, warning·실행 로그, commit·브랜치 메타데이터.
               (hash 필드를 계산 대상에 넣으면 자기참조로 값이 안정될 수 없다.)
      탐지 0건이면 generate_report가 호출되지 않으므로(pipeline.py 317-324 TN 메시지 경로)
      null을 기록한다.
    - phase1_system_prompt_sha256: Phase 1 실행에 사용된 시스템 프롬프트
      (_build_sonnet_solo_prompt — DB 혼동쌍 주입, 기사 무관)의 hash.
    """
    hashes = {
        "article_body_sha256": _sha256_text(article_body),
        "article_title_sha256": _sha256_text(title),
        "analysis_input_sha256": _sha256_canonical(
            {"article_text": article_body, "title": title}
        ),
        "detections_canonical_sha256": _sha256_canonical(
            sorted(detections, key=_canonical_dumps)
        ),
        "detections_ordered_sha256": _sha256_canonical(detections),
        "ethics_snapshot_sha256": _sha256_canonical(
            sorted(ethics_dicts, key=_canonical_dumps)
        ),
        "phase1_system_prompt_sha256": (
            _sha256_text(phase1_system_prompt) if phase1_system_prompt is not None else None
        ),
    }
    if validated_codes:
        hashes["report_input_sha256"] = _sha256_canonical({
            "article_text": article_body,
            "pattern_ids": pattern_ids,
            "detections": detections,
            "overall_assessment": overall_assessment,
            "meta_patterns": [],
            "article_context": article_context,
            "ethics_refs": ethics_dicts,
        })
    else:
        hashes["report_input_sha256"] = None
    return hashes


def build_capture_validation(
    validated_codes: list[str], ethics_dicts: list[dict], forensic: dict
) -> dict:
    """Task 1 — 별도 조회한 규범을 기준으로 patterns_without_ethics를 재계산.

    forensic.patterns_without_ethics는 run_sonnet=False일 때 pipeline 내부 규범 조회가
    수행되지 않아 validated 전체로 채워진다(pipeline.py 341-343). 원본 forensic은
    그대로 보존하고, 재계산 결과는 이 필드로만 기록한다.
    재계산 로직: 규범 refs에 등장하는 pattern_code 집합을 구하고,
    validated 패턴 중 그 집합에 없는 것만 without에 남긴다.
    """
    ref_codes = sorted({d.get("pattern_code", "") for d in ethics_dicts} - {""})
    validated_set = set(validated_codes)
    recomputed_without = sorted(validated_set - set(ref_codes))
    forensic_without = sorted(forensic.get("patterns_without_ethics", []))
    consistent = forensic_without == recomputed_without
    cv = {
        "patterns_with_ethics": ref_codes,
        "patterns_without_ethics": recomputed_without,
        "forensic_consistency": consistent,
        "difference_reason": None if consistent else (
            "run_sonnet=False로 pipeline 내부 ethics 조회가 수행되지 않음 — "
            "forensic.patterns_without_ethics는 validated 전체로 채워진다(pipeline.py 341-343). "
            "본 필드는 runner가 별도 조회한 규범 refs 기준 재계산값이다."
        ),
    }
    subset_ok = set(ref_codes) <= validated_set
    cv["ethics_subset_of_validated"] = subset_ok
    if not subset_ok:
        cv["subset_violation_codes"] = sorted(set(ref_codes) - validated_set)
    return cv


# ── Task 6: 진단 덤프 자동 아카이브 ────────────────────────────────────────
def _diag_file_set() -> set:
    if not DIAG_SRC_DIR.exists():
        return set()
    return set(DIAG_SRC_DIR.glob("diagnostic_*.json"))


def archive_new_diagnostics(before: set, fid: str, run_tag: str) -> dict:
    """실행 전후 파일 목록 차이를 계산해 신규 덤프를 아카이브한다.

    - 정확히 1개면 runs/diagnostics/<fid>/<run_tag>.json 으로 이동
      (사본 hash 동일성 확인 후 원본 삭제).
    - 0개면 경고만 기록(파이프라인의 덤프 실패는 비중단 설계).
    - 2개 이상이면 임의로 연결하지 않고 unmatched/로 이동하고 사유를 기록.
    """
    new_files = sorted(_diag_file_set() - before)
    if not new_files:
        return {"diagnostic_path": None, "diagnostic_sha256": None,
                "note": "실행 중 신규 진단 덤프가 관찰되지 않음"}
    if len(new_files) == 1:
        src = new_files[0]
        dst_dir = DIAG_ARCHIVE_DIR / fid
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{run_tag}.json"
        data = src.read_bytes()
        dst.write_bytes(data)
        src_sha = hashlib.sha256(data).hexdigest()
        dst_sha = hashlib.sha256(dst.read_bytes()).hexdigest()
        if src_sha != dst_sha:
            raise RuntimeError(f"진단 덤프 아카이브 hash 불일치: {src} → {dst}")
        src.unlink()
        rel = dst.relative_to(ROOT)
        return {"diagnostic_path": str(rel), "diagnostic_sha256": dst_sha}
    # 복수 신규 파일 — 임의 매핑 금지
    moved = []
    unmatched_dir = DIAG_ARCHIVE_DIR / "unmatched"
    unmatched_dir.mkdir(parents=True, exist_ok=True)
    for src in new_files:
        dst = unmatched_dir / src.name
        dst.write_bytes(src.read_bytes())
        if hashlib.sha256(dst.read_bytes()).hexdigest() != hashlib.sha256(src.read_bytes()).hexdigest():
            raise RuntimeError(f"unmatched 이동 hash 불일치: {src}")
        src.unlink()
        moved.append(str(dst.relative_to(ROOT)))
    return {"diagnostic_path": None, "diagnostic_sha256": None,
            "note": f"단일 실행에서 신규 덤프 {len(new_files)}개 관찰 — 임의 매핑 없이 unmatched/로 이동: {moved}"}


# ── capture 본체 ───────────────────────────────────────────────────────────
def run_one(fixture: dict, run_tag: str, mods: SimpleNamespace) -> Path:
    fid = fixture["fixture_id"]
    title = fixture["title"]
    article_text = fixture["article_text"]

    # 입력 무결성 검증 — fixtures.json에 기록된 hash와 일치해야 한다
    input_sha = _sha256_text(title + "\n" + article_text)
    if input_sha != fixture.get("article_sha256"):
        raise RuntimeError(
            f"[{fid}] fixtures.json의 article_sha256와 입력 텍스트가 불일치 — 표본 오염 의심"
        )

    print(f"\n[{fid}] ({run_tag}) 분석 시작 — {len(article_text)}자, title={title[:40]!r}")
    diag_before = _diag_file_set()
    t0 = time.time()
    result = mods.analyze_article(article_text, run_sonnet=False, title=title)
    elapsed = time.time() - t0

    pm = result.pattern_result
    detections = mods.build_haiku_dicts(pm, include_report_meta=True)
    pattern_ids = list(pm.validated_pattern_ids or [])
    pattern_codes = sorted(pm.validated_pattern_codes or [])
    forensic = result.phase1_forensic or {}
    article_context = forensic.get("article_context", "")

    # 그 시점의 윤리규범 조회(읽기 전용 RPC) — generate_report 내부 호출과 동일 함수·인자
    sb_url, sb_key = mods.get_supabase_config()
    ethics_refs = []
    if pattern_ids:
        ethics_refs = mods.fetch_ethics_for_patterns(
            pattern_ids, sb_url, sb_key, article_context=article_context or "general",
        )
    ethics_dicts = [asdict(er) for er in ethics_refs]

    true_negative_candidate = len(pattern_codes) == 0
    # 규범 0건 경고 — 탐지 0건(순수 TN 후보) 표본에는 적용하지 않는다
    ethics_empty_warning = bool(pattern_ids) and not ethics_dicts and not true_negative_candidate

    capture_validation = build_capture_validation(pattern_codes, ethics_dicts, forensic)

    # Phase 1 시스템 프롬프트 hash — 기사 무관, capture 시점 DB 혼동쌍 기준
    try:
        phase1_prompt = mods.pattern_matcher._build_sonnet_solo_prompt(sb_url, sb_key)
    except Exception as e:
        print(f"  ⚠️ Phase1 시스템 프롬프트 빌드 실패 — hash null 기록: {type(e).__name__}")
        phase1_prompt = None

    semantic_hashes = compute_semantic_hashes(
        title=title,
        article_body=article_text,
        pattern_ids=pattern_ids,
        detections=detections,
        overall_assessment=result.overall_assessment,
        article_context=article_context,
        ethics_dicts=ethics_dicts,
        validated_codes=pattern_codes,
        phase1_system_prompt=phase1_prompt,
    )

    diag_info = archive_new_diagnostics(diag_before, fid, run_tag)

    snapshot = {
        "snapshot_version": SNAPSHOT_VERSION,
        "fixture_id": fid,
        "run_tag": run_tag,
        "generated_at": datetime.now().astimezone().isoformat(),
        "git_commit": _git_commit(),
        "entrypoint": ENTRYPOINT_NOTE,
        "run_sonnet": False,
        "supabase_host": urlparse(sb_url).netloc or sb_url,
        "article": {
            "title": title,
            "text": article_text,
            "sha256": input_sha,
            "chars": len(article_text),
            "url": fixture.get("url", ""),
            "publisher": fixture.get("publisher", ""),
            "source": fixture.get("source", ""),
            "characteristic": fixture.get("characteristic", ""),
            "selection_reason": fixture.get("selection_reason", ""),
        },
        "phase1": {
            "model": forensic.get("phase1_model", ""),
            "validated_pattern_ids": pattern_ids,
            "validated_pattern_codes": pattern_codes,
            "detections": detections,
            "overall_assessment": result.overall_assessment,
            "article_context": article_context,
            "forensic": forensic,
        },
        "ethics": {
            "count": len(ethics_dicts),
            "empty_warning": ethics_empty_warning,
            "refs": ethics_dicts,
        },
        "true_negative_candidate": true_negative_candidate,
        "capture_validation": capture_validation,
        **semantic_hashes,
        "semantic_hash_provenance": {
            "basis": "capture",
            "computed_at": datetime.now().astimezone().isoformat(),
            "code": "scripts/report_quality_runner.py compute_semantic_hashes()",
        },
        "diagnostic_path": diag_info.get("diagnostic_path"),
        "diagnostic_sha256": diag_info.get("diagnostic_sha256"),
        "stability_digest": _stability_digest(pattern_codes, detections),
        "timing": {
            "pipeline_total_seconds": round(result.total_seconds, 2),
            "wall_seconds": round(elapsed, 2),
            "embedding_tokens": result.embedding_tokens,
        },
    }
    if diag_info.get("note"):
        snapshot["diagnostic_note"] = diag_info["note"]

    out_dir = CANDIDATES_DIR / fid
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_tag}.json"
    out_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    file_sha = _sha256_text(out_path.read_text(encoding="utf-8"))

    # 재현성 확인 — 저장된 파일을 다시 읽어 동일 payload에서 같은 hash가 나오는지 검증
    _verify_hash_reproducibility(out_path, phase1_prompt)

    # Task 1 assertion — 규범이 매핑된 패턴 집합 ⊆ validated 패턴 집합.
    # 스냅샷 저장 이후에 검사한다(위반 시에도 관찰 데이터는 보존).
    if not capture_validation["ethics_subset_of_validated"]:
        raise SystemExit(
            f"[{fid}] ({run_tag}) DISCUSS: 규범 refs의 pattern_code가 validated 집합을 벗어남 — "
            f"{capture_validation.get('subset_violation_codes')}. "
            f"스냅샷은 {out_path}에 보존됨. 실제 반환 구조를 보고하고 지시를 기다릴 것."
        )

    sev_map = {d["pattern_code"]: d["severity"] for d in detections}
    print(f"[{fid}] ({run_tag}) 완료 — {elapsed:.1f}s")
    print(f"  확정 패턴: {pattern_codes or '(없음)'}")
    print(f"  severity : {sev_map or '-'}")
    print(f"  규범     : {len(ethics_dicts)}건"
          + ("  ⚠️ 규범 0건 — 코드/설정 점검 필요" if ethics_empty_warning else "")
          + ("  [true_negative_candidate]" if true_negative_candidate else ""))
    print(f"  forensic_consistency: {capture_validation['forensic_consistency']}")
    print(f"  안정성 digest: {snapshot['stability_digest'][:16]}")
    print(f"  진단 덤프: {diag_info.get('diagnostic_path')}")
    print(f"  저장: {out_path}")
    print(f"  파일 sha256: {file_sha}")
    return out_path


def _verify_hash_reproducibility(snapshot_path: Path, phase1_prompt: str | None) -> None:
    """저장된 스냅샷을 다시 읽어 semantic hash를 재계산, 기록값과 일치하는지 확인."""
    s = json.loads(snapshot_path.read_text(encoding="utf-8"))
    recomputed = compute_semantic_hashes(
        title=s["article"]["title"],
        article_body=s["article"]["text"],
        pattern_ids=s["phase1"]["validated_pattern_ids"],
        detections=s["phase1"]["detections"],
        overall_assessment=s["phase1"]["overall_assessment"],
        article_context=s["phase1"]["article_context"],
        ethics_dicts=s["ethics"]["refs"],
        validated_codes=s["phase1"]["validated_pattern_codes"],
        phase1_system_prompt=phase1_prompt,
    )
    mismatches = [k for k, v in recomputed.items() if s.get(k) != v]
    if mismatches:
        raise RuntimeError(f"semantic hash 재현성 검증 실패: {mismatches} @ {snapshot_path}")
    print("  semantic hash 재현성: OK")


def main():
    # 순서:
    #   1) argparse 처리
    #   2) --ids 필수 여부 확인
    #   3) fixtures.json 로드 및 요청 ID 유효성 확인
    #   4) 전체 대상 candidate·diagnostic 충돌 사전 검사 (전수 완료 후 다음 단계)
    #   5) 위 검사를 모두 통과한 경우에만 load_environment()
    #   6) pipeline 모듈 로드
    #   7) capture 실행
    # 우회 옵션(--overwrite류)은 만들지 않는다.
    ap = argparse.ArgumentParser(description="리포트 품질 진단용 표본 고정 러너 (v2)")
    ap.add_argument(
        "--ids", nargs="*", default=None,
        help="실행할 fixture_id 목록 — 필수. 전체 fixture 자동 실행은 허용하지 않는다.",
    )
    ap.add_argument("--run-tag", default="r1", help="실행 태그(기본 r1)")
    ap.add_argument(
        "--env-file", default=None,
        help="이 파일의 키를 명시적으로 우선(override)한다. 미지정 시 셸 env 우선(placeholder면 명시적 실패).",
    )
    args = ap.parse_args()

    if not args.ids:
        raise SystemExit(
            "--ids를 반드시 명시하세요. 전체 fixture 자동 실행은 허용하지 않습니다."
        )

    manifest = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    fixtures = [f for f in manifest["fixtures"] if f["fixture_id"] in args.ids]
    missing = set(args.ids) - {f["fixture_id"] for f in fixtures}
    if missing:
        raise SystemExit(f"fixtures.json에 없는 id: {sorted(missing)}")

    # 충돌 사전 검사 — 전체 대상에 대해 먼저 완료. 하나라도 기존 파일이 있으면
    # 다른 fixture의 실행도 시작하지 않고 즉시 중단한다.
    for fx in fixtures:
        fid = fx["fixture_id"]
        cand = CANDIDATES_DIR / fid / f"{args.run_tag}.json"
        if cand.exists():
            raise SystemExit(
                f"기존 candidate는 덮어쓸 수 없습니다: {cand}. 새 run tag를 사용하세요."
            )
        diag = DIAG_ARCHIVE_DIR / fid / f"{args.run_tag}.json"
        if diag.exists():
            raise SystemExit(
                f"기존 diagnostic은 덮어쓸 수 없습니다: {diag}. 새 run tag를 사용하세요."
            )

    load_environment(args.env_file)
    mods = _load_pipeline_modules()

    print(f"표본 {len(fixtures)}건 실행 (run_tag={args.run_tag})")
    print(f"기준: {ENTRYPOINT_NOTE}")
    for fx in fixtures:
        run_one(fx, args.run_tag, mods)


if __name__ == "__main__":
    main()
