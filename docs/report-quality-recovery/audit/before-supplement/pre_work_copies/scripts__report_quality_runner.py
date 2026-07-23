#!/usr/bin/env python3
"""
report_quality_runner.py — 리포트 품질 진단용 표본 고정 러너.

목적:
  docs/report-quality-recovery/fixtures/fixtures.json 에 고정된 표본 기사에 대해
  현재 파이프라인의 Phase 1 탐지 결과 + 그 시점의 윤리규범 조회 결과를
  재현 가능한 스냅샷 JSON으로 저장한다.

원칙:
  - core.pipeline.analyze_article 를 직접 import 해 호출한다.
    운영 API(backend/main.py /analyze)·URL 캐시(get_cached_analysis)·
    DB 저장(save_analysis_result)은 일절 경유하지 않는다.
  - run_sonnet=False 로 호출한다. Phase 2 리포트 생성은 이 스크립트의
    범위가 아니다(표본 고정 전용).
  - 윤리규범은 fetch_ethics_for_patterns()를 별도 호출해 그 시점의
    전체 정보를 스냅샷에 포함한다(읽기 전용 RPC).
  - DB에 대한 쓰기·삭제·마이그레이션은 수행하지 않는다.

사용:
  python scripts/report_quality_runner.py                       # 표본 전체 1회(run_tag=r1)
  python scripts/report_quality_runner.py --ids PAST-DETENTION  # 특정 표본만
  python scripts/report_quality_runner.py --ids E-12 --run-tag r2   # 반복 실행(안정성 확인)

저장 위치:
  docs/report-quality-recovery/runs/snapshots/<fixture_id>.json          (run_tag=r1)
  docs/report-quality-recovery/runs/snapshots/<fixture_id>__<run_tag>.json (그 외)
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# override=True: 셸에 자리표시자 ANTHROPIC_API_KEY가 있어도 프로젝트 .env를 우선한다
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT / "backend"))

from core.pipeline import analyze_article, _build_haiku_dicts  # noqa: E402
from core.report_generator import fetch_ethics_for_patterns  # noqa: E402
from core.db import _get_supabase_config  # noqa: E402

FIXTURES_PATH = ROOT / "docs" / "report-quality-recovery" / "fixtures" / "fixtures.json"
SNAP_DIR = ROOT / "docs" / "report-quality-recovery" / "runs" / "snapshots"

ENTRYPOINT_NOTE = (
    "core.pipeline.analyze_article 직접 호출 — 운영 API(/analyze), "
    "URL 캐시(get_cached_analysis), DB 저장(save_analysis_result) 미경유"
)


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


def _stability_digest(codes: list[str], detections: list[dict]) -> str:
    """반복 실행 비교용 요약 해시 — (pattern_code, severity) 정렬 쌍 기준."""
    pairs = sorted((d.get("pattern_code", ""), d.get("severity", "")) for d in detections)
    payload = json.dumps({"codes": sorted(codes), "pairs": pairs}, ensure_ascii=False)
    return _sha256_text(payload)


def run_one(fixture: dict, run_tag: str) -> Path:
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
    t0 = time.time()
    result = analyze_article(article_text, run_sonnet=False, title=title)
    elapsed = time.time() - t0

    pm = result.pattern_result
    detections = _build_haiku_dicts(pm, include_report_meta=True)
    pattern_ids = list(pm.validated_pattern_ids or [])
    pattern_codes = sorted(pm.validated_pattern_codes or [])
    forensic = result.phase1_forensic or {}
    article_context = forensic.get("article_context", "")

    # 그 시점의 윤리규범 조회(읽기 전용 RPC) — Phase 2가 사용할 것과 동일한 함수·인자
    sb_url, sb_key = _get_supabase_config()
    ethics_refs = []
    if pattern_ids:
        ethics_refs = fetch_ethics_for_patterns(
            pattern_ids, sb_url, sb_key, article_context=article_context or "general",
        )
    ethics_dicts = [asdict(er) for er in ethics_refs]
    ethics_empty_warning = bool(pattern_ids) and not ethics_dicts

    snapshot = {
        "snapshot_version": "rq_v1",
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
        "stability_digest": _stability_digest(pattern_codes, detections),
        "timing": {
            "pipeline_total_seconds": round(result.total_seconds, 2),
            "wall_seconds": round(elapsed, 2),
            "embedding_tokens": result.embedding_tokens,
        },
    }

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{fid}.json" if run_tag == "r1" else f"{fid}__{run_tag}.json"
    out_path = SNAP_DIR / fname
    out_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    file_sha = _sha256_text(out_path.read_text(encoding="utf-8"))

    sev_map = {d["pattern_code"]: d["severity"] for d in detections}
    print(f"[{fid}] ({run_tag}) 완료 — {elapsed:.1f}s")
    print(f"  확정 패턴: {pattern_codes or '(없음)'}")
    print(f"  severity : {sev_map or '-'}")
    print(f"  규범     : {len(ethics_dicts)}건" + ("  ⚠️ 규범 0건 — 코드/설정 점검 필요" if ethics_empty_warning else ""))
    print(f"  안정성 digest: {snapshot['stability_digest'][:16]}")
    print(f"  저장: {out_path}")
    print(f"  파일 sha256: {file_sha}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="리포트 품질 진단용 표본 고정 러너")
    ap.add_argument("--ids", nargs="*", default=None, help="실행할 fixture_id 목록(생략 시 전체)")
    ap.add_argument("--run-tag", default="r1", help="실행 태그(기본 r1). r1 외에는 파일명에 접미사로 붙는다")
    args = ap.parse_args()

    manifest = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    fixtures = manifest["fixtures"]
    if args.ids:
        fixtures = [f for f in fixtures if f["fixture_id"] in args.ids]
        missing = set(args.ids) - {f["fixture_id"] for f in fixtures}
        if missing:
            raise SystemExit(f"fixtures.json에 없는 id: {sorted(missing)}")

    print(f"표본 {len(fixtures)}건 실행 (run_tag={args.run_tag})")
    print(f"기준: {ENTRYPOINT_NOTE}")
    for fx in fixtures:
        run_one(fx, args.run_tag)


if __name__ == "__main__":
    main()
