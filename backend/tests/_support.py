# backend/tests/_support.py
"""테스트 공용 헬퍼. 네트워크는 전부 여기서 모킹한다."""

import io
import os
import socket

import requests
from requests.structures import CaseInsensitiveDict

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_fixture(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as handle:
        return handle.read()


def make_response(body: bytes = b"", status: int = 200, content_type: str = "text/html",
                  url: str = "https://example-news.co.kr/article/1234",
                  extra_headers=None) -> requests.Response:
    """실제 requests가 만들어 주는 것과 같은 형태의 응답 객체.

    `encoding`은 requests가 쓰는 것과 같은 함수로 채운다 — charset이 없는
    text/* 응답에 'ISO-8859-1'이 들어가야 스크레이퍼의 인코딩 분기가 재현된다.
    """
    headers = CaseInsensitiveDict()
    if content_type is not None:
        headers["Content-Type"] = content_type
    for key, value in (extra_headers or {}).items():
        headers[key] = value

    response = requests.Response()
    response.status_code = status
    response.url = url
    response.headers = headers
    response.encoding = requests.utils.get_encoding_from_headers(headers)
    response.raw = io.BytesIO(body)
    return response


def make_parsed_response(body: bytes = b"", content_type: str = "text/html",
                         url: str = "https://example-news.co.kr/article/1234") -> requests.Response:
    """safe_fetch가 돌려주는 것과 같은, 본문을 이미 읽어 둔 응답 객체."""
    response = make_response(body=body, content_type=content_type, url=url)
    response._content = body
    response._content_consumed = True
    return response


def addrinfo(ip: str, port: int = 80):
    if ":" in ip:
        return (socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, port, 0, 0))
    return (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))


def fake_dns(*ips: str):
    """호스트 이름을 주어진 IP들로 해석하는 가짜 getaddrinfo."""
    def _resolve(host, port, *args, **kwargs):
        try:  # IP 리터럴이면 그대로 돌려준다
            socket.inet_pton(socket.AF_INET6 if ":" in host else socket.AF_INET, host)
            return [addrinfo(host, port or 80)]
        except (OSError, ValueError):
            pass
        return [addrinfo(ip, port or 80) for ip in ips]
    return _resolve


def dns_failure(host, port, *args, **kwargs):
    raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")


class SequenceGet:
    """requests.get 대역 — 준비한 응답을 순서대로 돌려주고 요청 URL을 기록한다."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requested_urls = []
        self.kwargs = []

    def __call__(self, url, **kwargs):
        self.requested_urls.append(url)
        self.kwargs.append(kwargs)
        if not self.responses:
            raise AssertionError(f"준비하지 않은 추가 요청이 발생했습니다: {url}")
        return self.responses.pop(0)


def redirect_response(location: str, status: int = 302, url: str = "https://example-news.co.kr/a"):
    return make_response(body=b"", status=status, content_type="text/html", url=url,
                         extra_headers={"Location": location})
