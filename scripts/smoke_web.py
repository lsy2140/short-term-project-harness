#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke_web.py — 웹 과제 스모크 (표준 라이브러리 urllib). 결과는 PASS/FAIL 표 + 종료 코드.
  python3 scripts/smoke_web.py http://127.0.0.1:8000 [--path /api/items?line=B] [--expect-text 알람] [--post /api/check '{"a":1}']
검사: GET / 200·HTML(viewport meta, h1 1개, 가로폭 고정 선언 없음) / --path 200·JSON 파싱 / --expect-text 포함 / --post JSON 응답 / 잘못된 JSON POST → 400 명시 거부 / 경로 탈출(../) 403·404
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

results = []


def rec(name, ok, detail=''):
    results.append((name, 'PASS' if ok else 'FAIL', detail))


def get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, '', ''
    except Exception as e:  # noqa
        return None, '', str(e)


def post(url, body, timeout=5):
    req = urllib.request.Request(url, data=body.encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:  # noqa
        return None, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('--path', action='append', default=[], help='200 + JSON 이어야 하는 경로')
    ap.add_argument('--expect-text', action='append', default=[], help='/ 에 포함돼야 하는 문자열')
    ap.add_argument('--post', nargs=2, metavar=('PATH', 'JSON'), help='POST 경로와 본문')
    a = ap.parse_args()
    base = a.base.rstrip('/')
    st, ct, body = get(base + '/')
    rec('GET / 200', st == 200, 'status=%s' % st)
    rec('html content-type', 'html' in ct.lower(), ct)
    rec('viewport meta', 'name="viewport"' in body or "name='viewport'" in body)
    rec('h1 exactly one', len(re.findall(r'<h1[\s>]', body)) == 1, '%d개' % len(re.findall(r'<h1[\s>]', body)))
    wide = re.findall(r'(?<![\w-])(?:min-)?width\s*:\s*(\d{4,})px', body)  # max-width 는 제외
    rec('no fixed width >= 1000px', not wide, ','.join(wide[:3]))
    rec('no external http(s) asset', not re.search(r'(src|href)=["\']https?://', body), '외부 URL 없음' if not re.search(r'(src|href)=["\']https?://', body) else '외부 자원 참조 있음(시험장에서 깨질 수 있음)')
    for t in a.expect_text:
        rec('text "%s"' % t, t in body)
    for p in a.path:
        st2, ct2, b2 = get(base + p)
        ok = st2 == 200
        try:
            json.loads(b2)
            okj = True
        except ValueError:
            okj = False
        rec('GET %s 200+JSON' % p, ok and okj, 'status=%s json=%s' % (st2, okj))
    if a.post:
        st3, b3 = post(base + a.post[0], a.post[1])
        rec('POST %s 2xx' % a.post[0], st3 is not None and 200 <= st3 < 300, 'status=%s' % st3)
        st4, _ = post(base + a.post[0], '{not json')
        rec('POST bad json -> 400', st4 == 400, 'status=%s' % st4)
    st5, _, _ = get(base + '/../../etc/passwd')
    rec('path traversal blocked', st5 in (400, 403, 404), 'status=%s' % st5)
    print('%-32s %-5s %s' % ('CHECK', 'RESULT', 'DETAIL'))
    for n, r, d in results:
        print('%-32s %-5s %s' % (n, r, d))
    fails = [r for r in results if r[1] == 'FAIL']
    print('RESULT: %d PASS / %d FAIL' % (len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
