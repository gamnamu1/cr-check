# backend/tests/conftest.py
"""pytest가 backend 모듈(`scraper`, `safe_fetch`, `extract_api`, `main`)을
운영과 같은 이름으로 import할 수 있게 경로를 잡아 준다.

운영에서는 `backend/`가 작업 디렉터리이므로(Dockerfile의 `uvicorn main:app`)
같은 flat import 경로를 재현한다.
"""

import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)

for path in (BACKEND_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
