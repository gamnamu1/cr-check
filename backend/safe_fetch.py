# backend/safe_fetch.py
"""[PR1] SSRF 방어가 적용된 fetch 계층.

`POST /extract` 전용이다. 기존 `/analyze` 경로(`ArticleScraper.scrape`의
`requests.get`)는 이 모듈을 사용하지 않으며, 그 동작은 그대로 유지된다.

공개 인터페이스는 `safe_fetch(url) -> SafeFetchResult` 하나다.
실패는 모두 `SafeFetchError(code, message)`로 올라오며, code는 지시서 2절의
오류 코드 표를 따른다.
"""

import ipaddress
import socket
import time
from dataclasses import dataclass
from email.message import Message
from typing import List, Set
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

from scraper import ArticleScraper

# 기존 스크레이퍼의 User-Agent를 그대로 재사용한다(문자열 중복·드리프트 방지).
_DEFAULT_HEADERS = dict(ArticleScraper().headers)

CONNECT_TIMEOUT = 5           # 연결 상한(초)
READ_TIMEOUT = 10             # 청크 간 유휴 상한(초)
TOTAL_TIMEOUT = 15            # 요청 시작 기준 전체 상한(초) — 수동 검사
MAX_REDIRECTS = 3             # 리디렉션 최대 추적 횟수
MAX_RESPONSE_BYTES = 2 * 1024 * 1024   # 압축 해제 기준 2MB
CHUNK_SIZE = 64 * 1024

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
ALLOWED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})

# DNS 해석 이전, 호스트 문자열 단계에서 걸러내는 내부 전용 이름
BLOCKED_HOST_NAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
})
BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".intranet",
    ".lan",
    ".home.arpa",
)

# 지시서 3-1의 4단계 금지 대역. 파이썬 버전별로 의미가 달라질 수 있는
# `is_private` 같은 플래그에만 기대지 않고 대역을 명시한다.
BLOCKED_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",      # CGNAT
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "224.0.0.0/4",        # multicast
        "240.0.0.0/4",        # reserved
    )
)
BLOCKED_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "::/128",             # unspecified
        "::1/128",            # loopback
        "fc00::/7",           # ULA
        "fe80::/10",          # link-local
        "ff00::/8",           # multicast
    )
)


class SafeFetchError(Exception):
    """fetch 단계 실패. code는 지시서 2절 오류 코드 표의 값."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class SafeFetchResult:
    """검증을 통과한 응답.

    response는 `requests.Response`이며 `encoding`·`apparent_encoding`·`text`·
    `content`를 그대로 제공한다(기존 스크레이퍼의 인코딩 로직이 무변경으로 동작).
    final_url은 리디렉션까지 마친 실제 도달 URL로, 매체별 파서 분기에만 쓴다.
    """

    response: requests.Response
    final_url: str


def safe_fetch(url: str) -> SafeFetchResult:
    """SSRF 검증을 거쳐 HTML을 가져온다. 디코딩은 하지 않는다."""
    started = time.monotonic()
    current_url = url
    seen: Set[str] = set()

    for _ in range(MAX_REDIRECTS + 1):
        _check_deadline(started)
        _validate_target(current_url)

        cycle_key = _cycle_key(current_url)
        if cycle_key in seen:
            raise SafeFetchError("SOURCE_FETCH_FAILED", "리디렉션이 순환합니다.")
        seen.add(cycle_key)

        response = _request(current_url)
        status = response.status_code

        if 300 <= status < 400:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise SafeFetchError(
                    "SOURCE_FETCH_FAILED", "리디렉션 응답에 이동할 주소가 없습니다."
                )
            # 상대경로 Location은 절대화한 뒤 다음 루프에서 1~4단계를 다시 검사한다.
            # HTML 안의 meta refresh·JavaScript 리디렉션은 검증 우회 경로가 되므로
            # 따라가지 않는다.
            current_url = urljoin(current_url, location.strip())
            continue

        if not 200 <= status < 300:
            response.close()
            raise SafeFetchError(
                "SOURCE_FETCH_FAILED", f"원격 서버가 {status} 상태로 응답했습니다."
            )

        _check_content_type(response)
        body = _read_body(response, started)

        # `requests.Response.content`가 하는 일과 같은 대입이다.
        # (Response.content 역시 `b"".join(self.iter_content(...))`를 _content에 넣는다)
        # 여기서는 크기·시간 상한을 걸고 읽었을 뿐이므로, 이후 response.text /
        # response.apparent_encoding은 비스트리밍 요청과 동일하게 동작한다.
        response._content = body
        response._content_consumed = True
        response.close()

        return SafeFetchResult(response=response, final_url=current_url)

    raise SafeFetchError("SOURCE_FETCH_FAILED", "리디렉션 횟수가 상한을 넘었습니다.")


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _validate_target(url: str) -> None:
    """지시서 3-1의 1~4단계 검증. 리디렉션 매 홉마다 다시 호출된다."""
    # 1. URL 파싱
    try:
        parts = urlsplit(url)
    except ValueError:
        raise SafeFetchError("INVALID_URL", "URL 형식이 올바르지 않습니다.")

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise SafeFetchError("INVALID_URL", "http 또는 https URL만 처리합니다.")

    if "@" in parts.netloc:
        raise SafeFetchError("INVALID_URL", "인증 정보가 포함된 URL은 처리하지 않습니다.")

    try:
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        raise SafeFetchError("INVALID_URL", "URL의 포트 표기가 올바르지 않습니다.")

    if not hostname:
        raise SafeFetchError("INVALID_URL", "URL에 호스트가 없습니다.")

    # 2. 호스트 문자열 검사
    host = hostname.strip(".").lower()
    if host in BLOCKED_HOST_NAMES or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise SafeFetchError("UNSAFE_URL", "내부 전용 호스트에는 접근하지 않습니다.")

    # 3. DNS 해석 — 결과 중 하나라도 금지 대역이면 호스트 전체를 거부한다
    #    (공개 IP와 사설 IP를 함께 반환하는 우회 차단)
    effective_port = port if port is not None else (443 if parts.scheme.lower() == "https" else 80)
    for address in _resolve(hostname, effective_port):
        if _is_blocked_ip(address):
            raise SafeFetchError("UNSAFE_URL", "허용되지 않는 IP 대역입니다.")

    # 4. 포트
    #    주의(잔여 위험): DNS 검증 시점과 실제 연결 시점 사이에 주소가 다시 해석될
    #    수 있다(DNS rebinding). 이를 막으려면 IP로 직접 연결하면서 Host 헤더와
    #    TLS SNI를 손수 다뤄야 하는데, 이는 네트워크 계층 재구현에 해당하므로
    #    지시서 3-1에 따라 채택하지 않는다. 대신 리디렉션 매 홉마다 1~4단계를
    #    다시 검사해 노출 구간을 좁힌다.
    if port is not None and port not in ALLOWED_PORTS:
        raise SafeFetchError("UNSAFE_URL", "허용되지 않는 포트입니다.")


def _resolve(hostname: str, port: int) -> List[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise SafeFetchError("SOURCE_FETCH_FAILED", "호스트 이름을 해석하지 못했습니다.")
    except OSError:
        raise SafeFetchError("SOURCE_FETCH_FAILED", "호스트 이름을 해석하지 못했습니다.")

    addresses: List[ipaddress._BaseAddress] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            raise SafeFetchError("SOURCE_FETCH_FAILED", "호스트 이름을 해석하지 못했습니다.")

    if not addresses:
        raise SafeFetchError("SOURCE_FETCH_FAILED", "호스트 이름을 해석하지 못했습니다.")
    return addresses


def _is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    """IPv4·IPv6·IPv4-mapped IPv6를 동일 기준으로 검사한다."""
    for candidate in _expand_address(address):
        if candidate.version == 4:
            networks = BLOCKED_IPV4_NETWORKS
        else:
            networks = BLOCKED_IPV6_NETWORKS
        if any(candidate in network for network in networks):
            return True
        if (
            candidate.is_loopback
            or candidate.is_private
            or candidate.is_link_local
            or candidate.is_multicast
            or candidate.is_reserved
            or candidate.is_unspecified
        ):
            return True
    return False


def _expand_address(address: ipaddress._BaseAddress) -> List[ipaddress._BaseAddress]:
    """IPv6가 IPv4 주소를 품고 있으면 그 IPv4도 함께 검사 대상에 넣는다."""
    candidates: List[ipaddress._BaseAddress] = [address]
    if isinstance(address, ipaddress.IPv6Address):
        for embedded in (address.ipv4_mapped, address.sixtofour):
            if embedded is not None:
                candidates.append(embedded)
        if address.teredo is not None:
            candidates.extend(address.teredo)
    return candidates


def _request(url: str) -> requests.Response:
    try:
        return requests.get(
            url,
            headers=_DEFAULT_HEADERS,
            allow_redirects=False,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except requests.exceptions.Timeout:
        raise SafeFetchError("SOURCE_TIMEOUT", "원격 서버가 시간 안에 응답하지 않았습니다.")
    except requests.exceptions.RequestException:
        raise SafeFetchError("SOURCE_FETCH_FAILED", "원격 서버에 연결하지 못했습니다.")


def _check_content_type(response: requests.Response) -> None:
    raw = response.headers.get("Content-Type") or ""
    holder = Message()
    # Content-Type이 아예 없으면 HTML로 볼 근거가 없으므로 거부 대상으로 둔다.
    holder["Content-Type"] = raw if raw.strip() else "application/octet-stream"
    mime = holder.get_content_type()
    if mime not in ALLOWED_CONTENT_TYPES:
        response.close()
        raise SafeFetchError(
            "UNSUPPORTED_CONTENT_TYPE", f"HTML이 아닌 응답입니다({mime})."
        )


def _read_body(response: requests.Response, started: float) -> bytes:
    total = 0
    chunks: List[bytes] = []
    try:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if time.monotonic() - started > TOTAL_TIMEOUT:
                response.close()
                raise SafeFetchError("SOURCE_TIMEOUT", "응답 수신이 시간 상한을 넘었습니다.")
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                response.close()
                raise SafeFetchError("RESPONSE_TOO_LARGE", "응답 본문이 너무 큽니다.")
            chunks.append(chunk)
    except SafeFetchError:
        raise
    except requests.exceptions.Timeout:
        response.close()
        raise SafeFetchError("SOURCE_TIMEOUT", "응답 수신이 시간 안에 끝나지 않았습니다.")
    except requests.exceptions.RequestException:
        response.close()
        raise SafeFetchError("SOURCE_FETCH_FAILED", "응답 본문을 받지 못했습니다.")
    return b"".join(chunks)


def _check_deadline(started: float) -> None:
    if time.monotonic() - started > TOTAL_TIMEOUT:
        raise SafeFetchError("SOURCE_TIMEOUT", "요청이 전체 시간 상한을 넘었습니다.")


def _cycle_key(url: str) -> str:
    """리디렉션 순환 판정용 키 — fragment만 떼어낸 URL."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
