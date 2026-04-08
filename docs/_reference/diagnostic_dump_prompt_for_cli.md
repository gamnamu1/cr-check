# 작업 지시: pipeline.py에 진단용 JSON 덤프 코드 추가

## 대상 파일
`backend/core/pipeline.py`

## 작업 개요
`analyze_article()` 함수에 파이프라인 중간 산출물을 JSON 파일로 저장하는 코드를 추가한다. 기존 로직은 일절 수정하지 않는다.

---

## 작업 1: 치환 전 원본 보존 변수 추가

현재 코드에서 아래 주석과 for 루프를 찾는다:

```python
# 결정론적 인용 후처리: cite 태그 → 규범 원문 치환 (3종 각각)
for report_type in ["comprehensive", "journalist", "student"]:
```

이 for 루프 **바로 위에** 다음 두 줄을 삽입한다:

```python
pre_citation_reports = {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]}
hallucinated_refs_log = {}
```

그리고 for 루프 **안에서**, 기존의 `resolve_citations` 호출 블록 내 `if hallucinated:` 바로 다음 줄에 이 한 줄을 추가한다:

```python
hallucinated_refs_log[report_type] = hallucinated
```

또한, `if hallucinated:` 조건과 무관하게 hallucinated가 빈 리스트인 경우에도 기록해야 하므로, 다음과 같이 처리한다:

```python
resolved, hallucinated = resolve_citations(text, rr.ethics_refs or [])
rr.reports[report_type] = resolved
hallucinated_refs_log[report_type] = hallucinated if hallucinated else []
if hallucinated:
    logger.warning(f"[{report_type}] 환각 ref 제거: {hallucinated}")
```

기존 except 블록 내에서도 `hallucinated_refs_log[report_type] = []`를 추가한다.

---

## 작업 2: JSON 덤프 코드 추가

`analyze_article()` 함수의 `return result` **바로 위에** 아래 코드 블록을 삽입한다.

```python
# ── 진단용 JSON 덤프 ────────────────────────────────────────
try:
    import json as _json
    from datetime import datetime as _dt
    from pathlib import Path as _Path

    _diag_dir = _Path(__file__).parent.parent / "diagnostics"
    _diag_dir.mkdir(exist_ok=True)
    _ts = _dt.now().strftime("%Y%m%d_%H%M%S")

    # Checkpoint 1: 청킹
    _cp1 = {
        "chunk_count": result.chunk_count,
        "avg_chunk_length": round(result.avg_chunk_length, 1),
        "chunks_preview": [
            {"index": i, "length": c.length, "preview": c.text[:80]}
            for i, c in enumerate(result.chunks)
        ],
    }

    # Checkpoint 2: 벡터 검색
    _cp2 = {
        "candidate_count": len(pm.vector_candidates),
        "vector_candidates": [
            {"pattern_code": vc.pattern_code, "pattern_name": vc.pattern_name, "similarity": round(vc.similarity, 4)}
            for vc in pm.vector_candidates
        ],
    }

    # Checkpoint 3: 패턴 식별
    _cp3 = {
        "overall_assessment": result.overall_assessment,
        "haiku_detections": [
            {"pattern_code": d.pattern_code, "matched_text": d.matched_text, "severity": d.severity, "reasoning": d.reasoning}
            for d in pm.haiku_detections
        ],
        "validated_pattern_codes": list(pm.validated_pattern_codes),
        "hallucinated_codes": list(pm.hallucinated_codes),
        "haiku_raw_response": pm.haiku_raw_response,
    }

    # Checkpoint 4, 5: 리포트 관련 (run_sonnet=True이고 패턴이 확정된 경우에만)
    _cp4 = {}
    _cp5 = {}
    if run_sonnet and pm.validated_pattern_ids:
        # CP4: 규범 조회
        _ethics = rr.ethics_refs or []
        _patterns_with_ethics = set(er.pattern_code for er in _ethics)
        _patterns_without = [pc for pc in pm.validated_pattern_codes if pc not in _patterns_with_ethics]
        _cp4 = {
            "ethics_ref_count": len(_ethics),
            "patterns_without_ethics": _patterns_without,
            "ethics_refs": [
                {
                    "pattern_code": er.pattern_code,
                    "ethics_code": er.ethics_code,
                    "ethics_title": er.ethics_title,
                    "ethics_tier": er.ethics_tier,
                    "full_text_length": len(er.ethics_full_text),
                    "full_text_preview": er.ethics_full_text[:300],
                    "relation_type": er.relation_type,
                    "strength": er.strength,
                }
                for er in _ethics
            ],
        }

        # CP5: 리포트 치환 전후
        _cp5 = {
            "pre_citation_reports": pre_citation_reports if 'pre_citation_reports' in dir() else {},
            "post_citation_reports": {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]},
            "hallucinated_refs_per_report": hallucinated_refs_log if 'hallucinated_refs_log' in dir() else {},
            "sonnet_raw_response": rr.sonnet_raw_response,
        }

    _diag = {
        "timestamp": _ts,
        "total_seconds": round(result.total_seconds, 2),
        "checkpoint_1_chunks": _cp1,
        "checkpoint_2_vector": _cp2,
        "checkpoint_3_pattern": _cp3,
        "checkpoint_4_ethics": _cp4,
        "checkpoint_5_report": _cp5,
    }

    _diag_path = _diag_dir / f"diagnostic_{_ts}.json"
    _diag_path.write_text(_json.dumps(_diag, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"진단 덤프 저장: {_diag_path}")

except Exception as _diag_err:
    logger.warning(f"진단 덤프 실패 (파이프라인에 영향 없음): {_diag_err}")
# ── 진단용 JSON 덤프 끝 ─────────────────────────────────────
```

---

## 작업 3: 변수 스코프 확인

`pre_citation_reports`와 `hallucinated_refs_log`는 `if run_sonnet and pm.validated_pattern_ids:` 블록 안에서만 생성된다. JSON 덤프 코드의 CP5에서 이 변수들을 참조할 때 `locals()` 대신 위 코드처럼 `'변수명' in dir()` 검사를 통해 방어한다.

---

## 금지 사항
- 기존 `analyze_article()` 함수의 로직, 변수명, 반환값, 에러 처리를 수정하지 않는다.
- import 문을 파일 상단에 추가하지 않는다 (덤프 블록 내부에서 로컬 import한다).
- 덤프 실패가 `return result`를 막아서는 안 된다.
