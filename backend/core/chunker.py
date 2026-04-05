# backend/core/chunker.py
"""
CR-Check — 기사 청킹 모듈

한국 온라인 뉴스의 특성을 반영한 의미 기반 병합 청킹.
마스터 플랜 섹션 4 준수.

절차:
1. 전처리 — 노이즈 제거 (캡션, 바이라인, 저작권 고지 등)
2. 의미 기반 병합 — 한 문장 줄바꿈 관행 대응, 300~500자 블록
3. 엣지케이스 — 단문/장문/리스트형
"""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """청킹 결과 단위."""
    text: str
    start_idx: int
    end_idx: int

    @property
    def length(self) -> int:
        return len(self.text)


# ── 1. 전처리: 노이즈 제거 ──────────────────────────────────────

# 한국 뉴스 사진 캡션 패턴
_CAPTION_PATTERNS = [
    r'/\s*[가-힣]{2,4}\s*기자',                          # /홍길동 기자
    r'○+\s*기자',                                        # ○○○ 기자
    r'\[사진[=\s]*[^\]]*\]',                              # [사진=연합뉴스]
    r'\(사진[=\s]*[^\)]*\)',                              # (사진=연합뉴스)
    r'사진\s*제공\s*[=:]\s*\S+',                          # 사진 제공=OO
    r'【[^\】]*사진[^\】]*】',                             # 【사진 캡션】
]

# 바이라인 패턴
_BYLINE_PATTERNS = [
    r'[가-힣]{2,4}\s+기자\s*[^\n]*$',                    # 홍길동 기자 (줄 끝)
    r'[가-힣]{2,4}\s+특파원\s*[^\n]*$',                  # 홍길동 특파원
    r'[가-힣]{2,4}\s+(?:인턴)?기자\s*=?\s*\S*@\S+',      # 홍길동 기자 = email
    r'\S+@\S+\.\S+',                                      # email 단독
    r'[가-힣]{2,4}\s+(?:선임)?기자$',                     # 줄 끝 기자명
]

# 저작권 고지
_COPYRIGHT_PATTERNS = [
    r'ⓒ[^\n]*',                                          # ⓒ 연합뉴스
    r'©[^\n]*',                                           # © 기호
    r'무단\s*(?:전재|복제|배포).*(?:금지|禁止)[^\n]*',    # 무단 전재 재배포 금지
    r'(?:Copyrights?|All\s*[Rr]ights?\s*[Rr]eserved)[^\n]*',
]

# 관련기사 / 광고성 문구
_MISC_NOISE_PATTERNS = [
    r'▶\s*관련\s*기사[^\n]*',                            # ▶ 관련 기사
    r'▶\s*.*?(?:바로가기|더보기|클릭)[^\n]*',
    r'\[관련기사\][^\n]*',
    r'☞\s*[^\n]*',                                        # ☞ 링크
    r'※\s*이\s*기사는.*(?:제공|배포)[^\n]*',              # ※ 뉴스와이어 제공
    r'<[^>]+>',                                            # HTML 태그 잔여
    r'\[.*?입력\s*\d{4}[.\-/]\d{2}[.\-/]\d{2}[^\]]*\]',  # [입력 2024.01.01]
    r'^[\s]*[-=]{3,}[\s]*$',                               # 구분선 (---, ===)
]

# 포털 전재 메타텍스트
_PORTAL_META_PATTERNS = [
    r'기사제보\s*및\s*보도자료[^\n]*',
    r'네이버에서\s*[^\n]*구독[^\n]*',
    r'좋아요\s*\d+\s*댓글\s*\d+',
    r'언론사\s*구독[^\n]*',
    r'^[\s]*기사원문[^\n]*$',
    r'SNS\s*공유[^\n]*',
]


def _compile_noise_patterns() -> list[re.Pattern]:
    """모든 노이즈 패턴을 컴파일."""
    all_patterns = (
        _CAPTION_PATTERNS
        + _BYLINE_PATTERNS
        + _COPYRIGHT_PATTERNS
        + _MISC_NOISE_PATTERNS
        + _PORTAL_META_PATTERNS
    )
    return [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in all_patterns]


_COMPILED_NOISE = _compile_noise_patterns()


def preprocess(text: str) -> str:
    """기사 원문에서 노이즈를 제거한다."""
    for pattern in _COMPILED_NOISE:
        text = pattern.sub('', text)

    # 연속 공백 줄 정리 (3개 이상 연속 줄바꿈 → 2개)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 각 줄의 앞뒤 공백 제거
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    # 전체 앞뒤 공백
    return text.strip()


# ── 2. 의미 기반 병합 청킹 ──────────────────────────────────────

MIN_CHUNK_SIZE = 100   # 이보다 짧은 단락은 병합
TARGET_MIN = 300       # 목표 최소 청크 크기
TARGET_MAX = 500       # 목표 최대 청크 크기
SHORT_ARTICLE = 500    # 이보다 짧으면 단일 청크


def _split_into_paragraphs(text: str) -> list[str]:
    """텍스트를 의미 단락으로 분리.

    - \\n\\n (빈 줄) → 의미적 경계로 존중
    - \\n 단독 → 한국 뉴스의 한 문장 줄바꿈 관행. 동일 단락 내.
    """
    # 빈 줄 기준으로 먼저 분리
    raw_blocks = re.split(r'\n\s*\n', text)

    paragraphs = []
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        # 블록 내 단일 줄바꿈은 공백으로 합침 (한 문장 줄바꿈 관행)
        merged = re.sub(r'\n', ' ', block).strip()
        if merged:
            paragraphs.append(merged)

    return paragraphs


def _merge_short_paragraphs(paragraphs: list[str]) -> list[str]:
    """MIN_CHUNK_SIZE 미만의 짧은 단락을 인접 단락과 병합."""
    if not paragraphs:
        return []

    merged = []
    buffer = paragraphs[0]

    for para in paragraphs[1:]:
        if len(buffer) < MIN_CHUNK_SIZE:
            # 짧은 버퍼 → 다음 단락과 합침
            buffer = buffer + ' ' + para
        elif len(para) < MIN_CHUNK_SIZE:
            # 다음 단락이 짧음 → 현재 버퍼에 합침
            buffer = buffer + ' ' + para
        else:
            merged.append(buffer)
            buffer = para

    if buffer:
        if len(buffer) < MIN_CHUNK_SIZE and merged:
            merged[-1] = merged[-1] + ' ' + buffer
        else:
            merged.append(buffer)

    return merged


def _split_large_chunk(text: str, max_size: int = TARGET_MAX) -> list[str]:
    """TARGET_MAX 초과 텍스트를 문장 단위로 분할."""
    # 한국어 문장 종결 패턴
    sentences = re.split(r'(?<=[.!?。다요])\s+', text)

    chunks = []
    current = ''

    for sent in sentences:
        if not sent.strip():
            continue
        candidate = (current + ' ' + sent).strip() if current else sent.strip()
        if len(candidate) > max_size and current:
            chunks.append(current.strip())
            current = sent.strip()
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _build_chunks_with_positions(texts: list[str], original: str) -> list[Chunk]:
    """청크 텍스트 리스트에서 원본 내 위치를 찾아 Chunk 객체를 생성."""
    chunks = []
    search_start = 0

    for text in texts:
        # 전처리로 공백이 변경되었을 수 있으므로, 핵심 단어로 근사 매칭
        # 가장 단순한 방법: 첫 20자로 위치 추정
        snippet = text[:20].strip()
        # 원본에서 공백/줄바꿈 무시하고 매칭 시도
        idx = original.find(snippet, search_start)
        if idx == -1:
            # fallback: 이전 청크 끝에서 시작
            idx = search_start

        start = idx
        end = min(start + len(text), len(original))
        chunks.append(Chunk(text=text, start_idx=start, end_idx=end))
        search_start = end

    return chunks


# ── 3. 메인 함수 ────────────────────────────────────────────────

def chunk_article(article_text: str) -> list[Chunk]:
    """기사 원문을 의미 기반 청크로 분할.

    Args:
        article_text: 기사 원문 텍스트 (스크래핑 결과)

    Returns:
        청크 리스트 (각 청크는 text, start_idx, end_idx 포함)
    """
    if not article_text or not article_text.strip():
        return []

    original = article_text

    # 1. 전처리
    cleaned = preprocess(article_text)

    if not cleaned:
        return []

    # 2. 극단적 단문 → 단일 청크
    if len(cleaned) <= SHORT_ARTICLE:
        return [Chunk(text=cleaned, start_idx=0, end_idx=len(original))]

    # 3. 단락 분리 (빈 줄 기준, 단일 줄바꿈은 병합)
    paragraphs = _split_into_paragraphs(cleaned)

    # 4. 짧은 단락 병합
    paragraphs = _merge_short_paragraphs(paragraphs)

    # 5. 큰 단락 분할
    final_texts = []
    for para in paragraphs:
        if len(para) > TARGET_MAX:
            final_texts.extend(_split_large_chunk(para, TARGET_MAX))
        else:
            final_texts.append(para)

    # 6. 최종 병합: TARGET_MIN 미만인 청크를 인접 청크와 합침
    if len(final_texts) > 1:
        merged = []
        buffer = final_texts[0]
        for t in final_texts[1:]:
            if len(buffer) < TARGET_MIN:
                buffer = buffer + ' ' + t
            else:
                merged.append(buffer)
                buffer = t
        if buffer:
            # 마지막 청크가 너무 짧으면 이전과 합침
            if len(buffer) < TARGET_MIN and merged:
                merged[-1] = merged[-1] + ' ' + buffer
            else:
                merged.append(buffer)
        final_texts = merged

    # 7. 위치 정보 부여
    chunks = _build_chunks_with_positions(final_texts, original)

    return chunks
