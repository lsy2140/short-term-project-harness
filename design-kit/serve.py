#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""serve.py — design-kit 폴더를 정적 서빙한다 (표준 라이브러리 http.server, Python 3.9).

  python3 design-kit/serve.py              # 0.0.0.0:8100 — 임시 점검 대역(앱 8000 · decide.py 8010 과 겹치지 않게)
  PORT=8101 python3 design-kit/serve.py    # 포트는 첫 인자 > PORT 환경변수 > 8100
  python3 design-kit/serve.py 8102 --dir .  # 다른 폴더를 서빙(과제 폴더에서 템플릿을 복사한 뒤)

동작: `/` → `/kit.html` 로 302(디렉터리 목록 대신 스타일가이드), 그 외는 디렉터리 안 파일만 서빙(`..` 는 http.server 가 정규화해 404).
Codex 가 백그라운드로 띄우고 시작 줄 `[서버] 포트 N 열었음 · 경로 · 종료` 를 그대로 보고한다(미리보기 탭에 포트를 넣는 것은 사람).
점검이 끝나면 끈다. 포트가 이미 쓰이면 exit 1 과 한 줄 안내(Windows 는 같은 포트를 겹쳐 열지 않게 SO_REUSEADDR 를 끈다).
"""
import argparse
import functools
import http.server
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8100   # 임시 점검 대역(AGENTS 1절 11: 앱 8000 · decide.py 8010 · 임시 점검 8100+)


class KitHandler(http.server.SimpleHTTPRequestHandler):
    """루트 요청을 kit.html 로 보내고, 캐시를 끈다(편집 즉시 반영)."""

    index_page = 'kit.html'

    def do_GET(self):
        if self.path in ('/', ''):
            self.send_response(302)
            self.send_header('Location', '/' + self.index_page)
            self.end_headers()
            return
        return super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):  # 한 줄 로그(경로·상태만)
        sys.stdout.write('%s %s\n' % (self.address_string(), fmt % args))
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description='design-kit 정적 서버')
    ap.add_argument('port', nargs='?', type=int, default=None, help='포트(기본: PORT 환경변수, 없으면 %d)' % DEFAULT_PORT)
    ap.add_argument('--dir', default=HERE, help='서빙할 폴더(기본: 이 파일이 있는 폴더)')
    ap.add_argument('--index', default='kit.html', help='/ 요청을 보낼 파일(기본 kit.html)')
    ap.add_argument('--host', default='0.0.0.0')
    a = ap.parse_args()
    port = a.port if a.port is not None else int(os.environ.get('PORT') or DEFAULT_PORT)
    directory = os.path.abspath(a.dir)
    if not os.path.isdir(directory):
        print('폴더가 없습니다: %s' % directory, file=sys.stderr)
        return 2
    KitHandler.index_page = a.index
    handler = functools.partial(KitHandler, directory=directory)
    http.server.ThreadingHTTPServer.allow_reuse_address = os.name != 'nt'   # Windows 의 SO_REUSEADDR 는 쓰는 포트를 겹쳐 연다
    try:
        srv = http.server.ThreadingHTTPServer((a.host, port), handler)
    except OSError as e:
        print('포트 %d 를 열지 못함: %s — 다른 포트(예 %d)를 첫 인자로 주거나 점유한 프로세스를 끝낸다' % (port, e, port + 1), file=sys.stderr)
        return 1
    port = srv.server_address[1]   # 0 을 주면 OS 가 고른 실제 포트
    print('serving %s' % directory, flush=True)
    print('[서버] 포트 %d 열었음 · 경로 /%s · 종료 kill %d  (바인드 %s, local http://127.0.0.1:%d/%s)'
          % (port, a.index, os.getpid(), a.host, port, a.index), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
