#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon.py — 낯선 실행 환경을 5초 안에 파악한다 (표준 라이브러리, Python 3.8+).
사전 체험 또는 과제 시작 직후 1회 실행. 출력의 "주의할 점"을 TASK.md 제약(Constraints)에 옮긴다.

  python3 scripts/recon.py            # 사람이 읽는 형태
  python3 scripts/recon.py --network  # pypi/github 도달 여부까지
  python3 scripts/recon.py --json     # 기계가 읽는 형태
비밀값은 출력하지 않는다(환경변수는 존재 여부만).
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass
import tempfile

TOOLS = ('python3', 'python', 'pip3', 'pip', 'git', 'make', 'node', 'npm', 'npx', 'sqlite3', 'curl', 'jq', 'codex')
MODULES = ('csv', 'json', 'sqlite3', 'statistics', 'unittest', 'http.server', 'zoneinfo', 'tomllib',
           'pytest', 'numpy', 'pandas', 'requests', 'openpyxl', 'flask', 'fastapi', 'matplotlib')
SECRET_ENV = ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'ANTHROPIC_API_KEY', 'CODEX_HOME', 'PORT')


def run(cmd, timeout=5):
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ''
    out = (done.stdout or done.stderr).strip()
    return out.splitlines()[0] if out else ''


def check_python():
    v = sys.version_info
    probes = {'Z suffix': '2026-10-31T01:00:00Z', '+0900 no colon': '2026-10-31T10:00:00+0900',
              'space sep': '2026-10-31 10:00:00', '+09:00': '2026-10-31T10:00:00+09:00'}
    iso = {}
    for label, text in probes.items():
        try:
            parsed = dt.datetime.fromisoformat(text)
            iso[label] = 'ok (aware)' if parsed.tzinfo else 'ok (NAIVE)'
        except ValueError:
            iso[label] = 'FAIL'
    return {'version': platform.python_version(), 'executable': sys.executable,
            'match_stmt': v >= (3, 10), 'pep604_union': v >= (3, 10), 'tomllib': v >= (3, 11), 'fromisoformat': iso}


def check_modules():
    found = {}
    for name in MODULES:
        try:
            found[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found[name] = False
    return found


def check_tools():
    out = {}
    for t in TOOLS:
        path = shutil.which(t)
        out[t] = (run([path, '--version']) or path) if path else ''
    return out


def check_git():
    if not shutil.which('git'):
        return {'available': False}
    inside = run(['git', 'rev-parse', '--is-inside-work-tree']) == 'true'
    info = {'available': True, 'inside_repo': inside,
            'user_name_set': bool(run(['git', 'config', 'user.name'])),
            'user_email_set': bool(run(['git', 'config', 'user.email']))}
    if inside:
        info['branch'] = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    return info


def check_fs_runtime():
    info = {'cwd': os.getcwd(), 'platform': platform.platform(), 'cpu': os.cpu_count(),
            'stdout_encoding': getattr(sys.stdout, 'encoding', None), 'LANG': os.environ.get('LANG', ''), 'TZ': os.environ.get('TZ', '')}
    try:
        with tempfile.NamedTemporaryFile(dir=os.getcwd(), suffix='.recon'):
            pass
        info['cwd_writable'] = True
    except OSError:
        info['cwd_writable'] = False
    try:
        info['disk_free_gb'] = round(shutil.disk_usage(os.getcwd()).free / 1024 ** 3, 1)
    except OSError:
        pass
    try:
        with open('/proc/meminfo') as fh:
            for line in fh:
                if line.startswith('MemTotal:'):
                    info['mem_gb'] = round(int(line.split()[1]) / 1024 ** 2, 1)
                    break
    except OSError:
        pass
    info['home_files'] = sorted(os.listdir(os.path.expanduser('~')))[:15] if os.path.isdir(os.path.expanduser('~')) else []
    return info


def check_network(enabled):
    if not enabled:
        return {'checked': False}
    import socket
    res = {}
    for host in ('pypi.org', 'github.com', 'api.openai.com'):
        try:
            with socket.create_connection((host, 443), timeout=3):
                res[host] = 'reachable'
        except OSError as e:
            res[host] = 'unreachable (%s)' % type(e).__name__
    return {'checked': True, 'targets': res}


def warnings(r):
    w = []
    iso = r['python']['fromisoformat']
    if iso.get('Z suffix') == 'FAIL':
        w.append("fromisoformat 이 'Z' 를 못 읽는다 → .replace('Z', '+00:00') 로 치환")
    if 'NAIVE' in iso.get('space sep', ''):
        w.append("'YYYY-MM-DD HH:MM:SS' 는 tzinfo 없음 → aware 시각과 비교하면 TypeError")
    if not r['python']['match_stmt']:
        w.append('match 문·X|Y 타입 표기 불가(3.10 미만) → if/elif, Optional 사용')
    if not r['tools'].get('git'):
        w.append('git 없음 → git clone 불가 → Plan C(RUN.md 막힘 결정 트리)')
    if not r['tools'].get('codex'):
        w.append('codex 명령이 PATH 에 없음 → 터미널에서 codex 실행 경로 확인')
    for m in ('pandas', 'numpy'):
        if not r['modules'].get(m):
            w.append('%s 없음 → 설치에 시간 쓰지 말고 표준 라이브러리(csv·sqlite3·statistics)로' % m)
    if not r['modules'].get('pytest'):
        w.append('pytest 없음 → unittest 사용(하네스 기본값)')
    if not r['fs'].get('cwd_writable'):
        w.append('현재 디렉터리에 쓸 수 없음 → 출력 경로 확보')
    return w


def render(r):
    L = []
    p = r['python']
    L.append('── Python  %s  (%s)' % (p['version'], p['executable']))
    L.append('   match문 %s · tomllib %s · fromisoformat: %s' % (
        '가능' if p['match_stmt'] else '불가', '가능' if p['tomllib'] else '불가',
        ', '.join('%s=%s' % (k, v) for k, v in p['fromisoformat'].items())))
    L.append('── 도구    ' + ' · '.join('%s=%s' % (k, (v[:28] if v else '없음')) for k, v in r['tools'].items()))
    present = [m for m, ok in r['modules'].items() if ok]
    missing = [m for m, ok in r['modules'].items() if not ok]
    L.append('── 모듈    있음: %s' % ', '.join(present))
    L.append('           없음: %s' % (', '.join(missing) or '-'))
    g = r['git']
    L.append('── git     %s' % ('없음' if not g.get('available') else ('저장소 안(%s)' % g.get('branch') if g.get('inside_repo') else '저장소 아님 (시험장은 git clone 만, 커밋 없음 — 기록은 out/debug·DECISIONS)')))
    f = r['fs']
    L.append('── 런타임  %s · CPU %s · 메모리 %sGB · 디스크 %sGB · cwd %s(쓰기 %s) · 인코딩 %s · TZ=%s' % (
        f['platform'][:40], f['cpu'], f.get('mem_gb', '?'), f.get('disk_free_gb', '?'), f['cwd'],
        '가능' if f.get('cwd_writable') else '불가', f['stdout_encoding'], f['TZ'] or '미설정'))
    L.append('── 홈 파일  %s' % ', '.join(f['home_files']))
    L.append('── 환경변수(존재만) ' + ', '.join('%s=%s' % (k, 'set' if v else '-') for k, v in r['env'].items()))
    n = r['network']
    L.append('── 네트워크 %s' % ('미확인(--network)' if not n.get('checked') else ', '.join('%s:%s' % kv for kv in n['targets'].items())))
    L.append('── 주의할 점')
    for w in r['warnings'] or ['특이사항 없음']:
        L.append('   ! ' + w)
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--network', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    r = {'python': check_python(), 'modules': check_modules(), 'tools': check_tools(), 'git': check_git(),
         'fs': check_fs_runtime(), 'env': {k: bool(os.environ.get(k)) for k in SECRET_ENV}, 'network': check_network(a.network)}
    r['warnings'] = warnings(r)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else render(r))


if __name__ == '__main__':
    main()
