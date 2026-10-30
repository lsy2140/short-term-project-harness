# -*- coding: utf-8 -*-
"""tests 패키지. python3 -m unittest -v 로 실행. 콘솔 인코딩이 UTF-8 이 아니어도 한글 테스트 이름이 깨지지 않게 한다."""
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass
