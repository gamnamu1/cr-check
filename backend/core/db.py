# backend/core/db.py
"""
CR-Check — Supabase 연결 공통 모듈
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

_LOCAL_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0."
    "EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)


def _get_supabase_config() -> tuple[str, str]:
    """Supabase URL + service key를 반환. 로컬 우선."""
    local_url = "http://127.0.0.1:54321"
    sb_url = os.environ.get("SUPABASE_URL", "")

    # SUPABASE_LOCAL=1 이면 로컬 강제, 또는 URL이 localhost면 로컬
    if os.environ.get("SUPABASE_LOCAL") or "127.0.0.1" in sb_url or "localhost" in sb_url:
        return local_url, _LOCAL_SERVICE_KEY

    # 로컬 실행 여부 확인
    try:
        r = httpx.get(
            f"{local_url}/rest/v1/patterns?select=id&limit=1",
            headers={"apikey": _LOCAL_SERVICE_KEY},
            timeout=5,
        )
        if r.status_code == 200:
            return local_url, _LOCAL_SERVICE_KEY
    except (httpx.ConnectError, httpx.ReadTimeout):
        pass

    # 클라우드 폴백
    cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return sb_url, cloud_key
