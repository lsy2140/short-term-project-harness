#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""with_server.py — 서버를 띄우고 포트가 열릴 때까지 기다린 뒤 명령을 실행하고 서버를 정리한다. (표준 라이브러리, Py3.9)
원본: https://github.com/anthropics/skills  skills/webapp-testing/scripts/with_server.py
      Copyright 2026 Anthropic, PBC — Apache License 2.0 (전문: LICENSES/Apache-2.0.txt)
변경 고지(Apache-2.0 제4조 (b)): 이 파일은 원본을 수정했다 — 단일 서버로 축약, PORT 환경변수 전달,
      Windows 프로세스 트리 정리(taskkill /T), 한국어 안내 문구. 변경 부분도 Apache License 2.0 으로 배포한다.

  python3 scripts/with_server.py --server "python3 app.py" --port 8000 -- python3 scripts/smoke_web.py http://127.0.0.1:8000
  python3 scripts/with_server.py --server "PORT=8000 python3 app.py" --port 8000 -- python3 -m unittest tests.test_http -v
종료 코드 = 실행한 명령의 종료 코드. 서버가 timeout 초 안에 안 뜨면 1.
"""
import argparse
import os
import signal
import socket
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass


def wait_port(host, port, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server', required=True, help='서버 기동 명령(셸)')
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--timeout', type=int, default=20)
    ap.add_argument('cmd', nargs=argparse.REMAINDER, help='-- 뒤에 실행할 명령')
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == '--' else a.cmd
    if not cmd:
        print('실행할 명령이 없습니다 (-- 뒤에 적으세요)', file=sys.stderr)
        return 2
    env = dict(os.environ)
    env.setdefault('PORT', str(a.port))
    kw = {'shell': True, 'env': env}
    if os.name != 'nt':
        kw['preexec_fn'] = os.setsid  # 프로세스 그룹 → killpg 로 손자까지 정리
    else:
        kw['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP  # Windows: taskkill /T 로 트리 정리
    server = subprocess.Popen(a.server, **kw)
    try:
        if not wait_port(a.host, a.port, a.timeout):
            print('서버가 %d초 안에 %s:%d 를 열지 않음' % (a.timeout, a.host, a.port), file=sys.stderr)
            return 1
        print('[with_server] %s:%d 준비 (%s)' % (a.host, a.port, a.server), flush=True)
        return subprocess.call(cmd, env=env)
    finally:
        try:
            if os.name != 'nt':
                os.killpg(os.getpgid(server.pid), signal.SIGTERM)
            else:
                # shell=True 는 cmd.exe 만 terminate 되고 python 서버가 고아로 남아 포트·파이프를 쥔다 → 트리째 종료
                subprocess.call(['taskkill', '/PID', str(server.pid), '/T', '/F'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            server.wait(timeout=5)
        except Exception:  # noqa
            try:
                server.kill()
            except Exception:  # noqa
                pass


if __name__ == '__main__':
    sys.exit(main())
