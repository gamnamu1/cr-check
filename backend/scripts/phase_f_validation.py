#!/usr/bin/env python3
"""Phase F 실행기 — Reserved Test Set 블라인드 평가.

Reserved Test Set은 리포지토리 외부의 격리 디렉토리에 보관된다.
이 스크립트는 Gamnamu가 수동으로 주입한 서브셋 파일만 읽으며,
Pool 디렉토리 절대 경로는 코드에 하드코딩하지 않는다.

주입 파일 스키마 (최상위 list):
    [
        {"id": "<str>", "url": "<str>", "label": {...}},
        ...
    ]

블라인드 원칙:
    label 필드는 이 스크립트에서 절대 로드하지 않는다.
    allowlist 방식으로 id + url 만 메모리에 올린다.
    채점은 phase_f_scoring.py가 사후 조인으로 수행한다.

사용:
    # 파일럿 (3건, seed 기반 재현 가능):
    python backend/scripts/phase_f_validation.py --pilot 3

    # 본실행 (17건, 파일럿 ID 제외):
    python backend/scripts/phase_f_validation.py --full \\
        --exclude-ids A-01,A-02,A-03

    # 주입 파일 스키마 검증만 (호출 없음):
    python backend/scripts/phase_f_validation.py --pilot 3 --dry-run

환경변수:
    CR_CHECK_API_URL    백엔드 URL (기본: 프로덕션)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path

import httpx

# ── 상수 ─────────────────────────────────────────────────────────
BACKEND_URL = os.environ.get(
    "CR_CHECK_API_URL", "https://cr-check-production.up.railway.app"
)
INJECT_PATH_DEFAULT = Path(
    "backend/diagnostics/phase_f/injected/reserved_subset_20.json"
)
RUN_BASE_DIR = Path("backend/diagnostics/phase_f")
ANALYZE_TIMEOUT_SEC = 600.0  # 분석은 최대 10분 소요 가능

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("phase_f")


# ── 블라인드 로더 ────────────────────────────────────────────────
def load_blind_subset(path: Path) -> list[dict]:
    """주입 파일에서 id + url 만 추출. label 필드는 메모리에 올리지 않는다.

    allowlist 방식으로 반드시 필요한 필드만 복사하여 레이블 우연 열람을
    코드 레벨에서 원천 차단한다.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"주입 파일이 없습니다: {path}\n"
            f"Gamnamu가 Pool에서 수동 선별한 서브셋을 이 경로에 배치해야 합니다.\n"
            f"(CLI는 Pool 디렉토리에 직접 접근하지 않습니다.)"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    # 최상위 형식 정규화: list 또는 {"candidates": [...]} 둘 다 허용
    if isinstance(raw, dict):
        if "candidates" in raw and isinstance(raw["candidates"], list):
            raw = raw["candidates"]
        else:
            raise ValueError(
                "주입 파일이 dict이지만 'candidates' 리스트를 찾을 수 없습니다"
            )
    if not isinstance(raw, list):
        raise ValueError(
            f"주입 파일 최상위는 리스트 또는 candidates 키를 포함한 dict여야 "
            f"합니다 (받음: {type(raw).__name__})"
        )
    items: list[dict] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"항목 {i}이 dict가 아닙니다: {type(item).__name__}")
        # Reserved Test Set v2 스키마: id/candidate_id + url/source_url 폴백
        item_id = item.get("id") or item.get("candidate_id")
        item_url = item.get("url") or item.get("source_url")
        if not item_id:
            raise ValueError(f"항목 {i}에 id/candidate_id 필드가 누락되었습니다")
        if not item_url:
            raise ValueError(f"항목 {i}에 url/source_url 필드가 누락되었습니다")
        # allowlist: id + url 만 복사. label 관련 필드는 메모리 진입 금지.
        items.append({"id": str(item_id), "url": str(item_url)})
    logger.info(f"블라인드 로딩 완료: {len(items)}건 (label 필드 미참조)")
    return items


# ── /analyze 호출 (재시도 포함) ──────────────────────────────────
def call_analyze(
    url: str, client: httpx.Client, max_retries: int = 5
) -> dict:
    """/analyze 엔드포인트 호출.

    서버 측 Phase 2 Bugfix(529 긴백오프, 429 즉시실패, JSON 4단 폴백)가
    LLM 레이어의 재시도를 이미 처리한다. 이 함수는 네트워크/HTTP 레이어의
    재시도만 담당한다.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.post(
                f"{BACKEND_URL}/analyze",
                json={"url": url},
                timeout=ANALYZE_TIMEOUT_SEC,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            last_exc = e
            if status == 529:
                wait = min(10 * (2**attempt), 60)
                logger.warning(
                    f"API 과부하(529), {wait}초 후 재시도 "
                    f"({attempt + 1}/{max_retries})"
                )
                if attempt == max_retries - 1:
                    raise
                time.sleep(wait)
            elif status == 429:
                logger.error(f"API 한도 초과(429), 재시도 없이 실패: {e}")
                raise
            else:
                logger.error(
                    f"HTTP 오류({status}), 시도 {attempt + 1}/{max_retries}: {e}"
                )
                if attempt == max_retries - 1:
                    raise
                time.sleep(2**attempt)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            last_exc = e
            logger.warning(
                f"네트워크 오류, 시도 {attempt + 1}/{max_retries}: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(f"unreachable — max_retries 소진: {last_exc}")


# ── 메인 ────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase F 블라인드 실행기 (Reserved Test Set)"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--pilot",
        type=int,
        metavar="N",
        help="파일럿 N건 실행 (seed 기반 무작위 샘플)",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="본실행 — 주입 파일의 모든 항목 (필요 시 --exclude-ids로 제외)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="파일럿 샘플링 시드"
    )
    parser.add_argument(
        "--exclude-ids",
        type=str,
        default="",
        help="쉼표로 구분된 제외 ID 목록 (본실행 시 파일럿 ID 제외용)",
    )
    parser.add_argument(
        "--inject-path",
        type=Path,
        default=INJECT_PATH_DEFAULT,
        help=f"주입 파일 경로 (기본: {INJECT_PATH_DEFAULT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="주입 파일 로드 + 스키마 검증만 수행 (API 호출 없음)",
    )
    return parser.parse_args()


def select_items(
    items: list[dict], args: argparse.Namespace
) -> tuple[list[dict], str]:
    """모드에 따라 실행 대상 항목을 선택."""
    if args.pilot:
        rng = random.Random(args.seed)
        selected = rng.sample(items, min(args.pilot, len(items)))
        mode_label = f"pilot-{args.pilot}"
    else:
        # --full
        exclude: set[str] = set()
        if args.exclude_ids:
            exclude = {s.strip() for s in args.exclude_ids.split(",") if s.strip()}
        selected = [it for it in items if it["id"] not in exclude]
        mode_label = (
            f"full-{len(selected)}"
            + (f"-excl-{len(exclude)}" if exclude else "")
        )
    return selected, mode_label


def main() -> None:
    args = parse_args()

    items = load_blind_subset(args.inject_path)
    selected, mode_label = select_items(items, args)
    logger.info(
        f"선택: {len(selected)}건 ({mode_label}) "
        f"— 주입 총 {len(items)}건"
    )

    if args.dry_run:
        logger.info("dry-run: 스키마 검증 완료. 실행 중단.")
        for item in selected:
            logger.info(f"  - {item['id']}: {item['url']}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUN_BASE_DIR / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"실행 시작: {mode_label} → {run_dir}")

    manifest: dict = {
        "mode": mode_label,
        "started_at": timestamp,
        "backend_url": BACKEND_URL,
        "inject_path": str(args.inject_path),
        "total": len(selected),
        "ids": [item["id"] for item in selected],
        "results": [],
    }

    def save_manifest() -> None:
        (run_dir / "_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    with httpx.Client() as client:
        for i, item in enumerate(selected, start=1):
            item_id = item["id"]
            url = item["url"]
            start = time.time()
            logger.info(f"[{i}/{len(selected)}] {item_id} 시작: {url}")
            try:
                analysis = call_analyze(url, client)
                duration = time.time() - start
                result_path = run_dir / f"result_{item_id}.json"
                result_path.write_text(
                    json.dumps(
                        {"id": item_id, "url": url, "analysis": analysis},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                manifest["results"].append(
                    {
                        "id": item_id,
                        "status": "ok",
                        "share_id": analysis.get("share_id"),
                        "is_cached": analysis.get("is_cached", False),
                        "duration_sec": round(duration, 2),
                    }
                )
                logger.info(
                    f"[{i}/{len(selected)}] {item_id} 완료 "
                    f"({duration:.1f}초, share_id={analysis.get('share_id')})"
                )
            except Exception as e:
                duration = time.time() - start
                manifest["results"].append(
                    {
                        "id": item_id,
                        "status": "error",
                        "error": f"{type(e).__name__}: {str(e)[:200]}",
                        "duration_sec": round(duration, 2),
                    }
                )
                logger.error(f"[{i}/{len(selected)}] {item_id} 실패: {e}")

            # 체크포인트: 3건마다
            if i % 3 == 0:
                save_manifest()
                logger.info(f"체크포인트 저장: {i}/{len(selected)}")

    manifest["finished_at"] = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_manifest()

    ok = sum(1 for r in manifest["results"] if r["status"] == "ok")
    err = sum(1 for r in manifest["results"] if r["status"] == "error")
    logger.info(f"\n실행 완료: {ok} 성공 / {err} 실패 → {run_dir}")


if __name__ == "__main__":
    main()
