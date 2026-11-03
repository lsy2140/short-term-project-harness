#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preflight.py — 제출 직전 점검 (표준 라이브러리만, Python 3.9)

사용:
  python3 scripts/preflight.py                      # 환경·TODO·비밀키·디버그 폴더·동결 해시·설명문·컴파일·과제 테스트
  python3 scripts/preflight.py --env                # 실행 환경만: python 버전·도구 유무·모듈·fromisoformat 프로브(테스트 없음)
  python3 scripts/preflight.py --freeze             # 복구본 .tmp/freeze_N/(N 은 1, 2, … 실행마다 증가) + tests/ 해시 기록. 사람만 실행
  python3 scripts/preflight.py --check-freeze       # 가장 최근 동결 이후 tests/ 변경 여부만
  python3 scripts/preflight.py --require out/result.csv README.md PLAN.md   # 필수 제출 파일 확인
  python3 scripts/preflight.py --tests tests        # 과제 테스트 폴더 지정(기본 tests)
  python3 scripts/preflight.py --harness-tests      # 하네스 도구 테스트(scripts/tests)도 돌린다 — 줄 때만 실행

debug-dir: out/debug 가 없으면 PASS. 폴더 수·총 파일 수 상한은 없다. 폴더당 5파일 초과는 PASS 상세에 적기만 하고,
           금지 패턴(*_before·*_protected_before*·chrome_profile·입력 복사본)만 WARN — python3 scripts/debug_dir.py --check 로 상세를 본다.
스캔 제외: .tmp/·out/debug 는 TODO·비밀키 스캔에서 빼고, work/(에이전트 로그)는 TODO 스캔만 뺀다(비밀키는 본다).
freeze: 복구본에는 work/ 가 들어가고 .tmp/·.agents/·data/·out/debug 는 빠진다.
tests: 과제 테스트(tests/)만 센다 — README 의 테스트 수는 이 줄이다.
harness-tests: --harness-tests 를 줄 때만 실행. 실패해도 WARN 이고 README 테스트 수에 넣지 않는다.
docstring: 과제 코드 함수의 설명문(입력·출력 줄)이 빠지면 WARN — python3 scripts/docmap.py --check 로 목록을 본다.

exit 0  검사한 항목이 모두 PASS (정답 증명은 아님)
exit 1  FAIL 있음
exit 2  검사한 항목이 0개 — 이 결과를 통과로 읽지 말 것
"""
import argparse
import compileall
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

ROOT = os.getcwd()
SKIP_DIRS = {'.git', '.agents', '__pycache__', 'node_modules', '.venv', 'venv', 'docs', '9. 참고_공개저장소', '.tmp'}
SKIP_RELDIRS = {os.path.join('out', 'debug'), os.path.join('design-kit', 'refs')}  # 디버그 기록·참고 DESIGN.md 원문(제3자 글, 'placeholder' 같은 단어 포함)은 제출물이 아니다
TODO_SKIP_TOP = {'work'}  # 에이전트 로그의 'TODO' 는 할 일 기록이지 미구현 표시가 아니다(비밀키 스캔은 한다)
TEXT_EXT = {'.py', '.md', '.txt', '.json', '.csv', '.toml', '.yaml', '.yml', '.html', '.js', '.sh'}
TODO_PAT = re.compile(r'\bTODO\b|\bFIXME\b|미구현|(?<![:.\w-])placeholder(?!\s*[=:])|XXX', re.I)  # HTML·JS 의 placeholder= 속성은 제외
SECRET_PAT = re.compile(r'(sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|(api[_-]?key|secret|password|token)\s*[=:]\s*["\'][^"\']{6,}["\'])', re.I)
TEMPLATE_FILES = {'TASK.md', 'DECISIONS.md', 'PLAN.md', 'RUN.md', 'AGENTS.md'}

ENV_TOOLS = ('python3', 'python', 'pip3', 'pip', 'git', 'node', 'npm', 'sqlite3', 'curl', 'jq', 'codex')
ENV_STDLIB = ('csv', 'json', 'sqlite3', 'statistics', 'unittest', 'http.server', 'zoneinfo')
ENV_OPTIONAL = ('pytest', 'numpy', 'pandas', 'requests', 'openpyxl', 'flask', 'fastapi', 'matplotlib')
ENV_VARS = ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_HOME', 'PORT')  # 존재 여부만 출력(값은 출력하지 않음)
ISO_PROBES = (  # (이름, 입력, 실패할 때 대처)
    ('Z', '2026-10-31T01:00:00Z', ".replace('Z', '+00:00') 로 바꾼 뒤 파싱"),
    ('+0900', '2026-10-31T10:00:00+0900', "콜론을 넣어 '+09:00' 으로 바꾼 뒤 파싱"),
    ('space', '2026-10-31 10:00:00', '형식을 직접 지정(strptime)'),
    ('+09:00', '2026-10-31T10:00:00+09:00', '형식을 직접 지정(strptime)'),
)

FREEZE_PARENT = '.tmp'
FREEZE_RE = re.compile(r'^freeze_(\d+)$')
FREEZE_META = 'tests.sha256.json'
FREEZE_SKIP = {'.tmp', '.git', '__pycache__', '.agents', 'data', 'node_modules', '.venv', 'venv', 'debug', 'refs'}  # .agents(스킬 원문)·data(입력 불변)·out/debug·design-kit/refs(참고 원문) 제외, work/ 는 포함

results = []  # (name, status, detail)


def rec(name, status, detail=''):
    results.append((name, status, detail))


def walk_text_files():
    for base, dirs, files in os.walk(ROOT):
        rel_base = os.path.relpath(base, ROOT)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and os.path.normpath(os.path.join(rel_base, d)) not in SKIP_RELDIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                yield os.path.join(base, f)


# ---------------------------------------------------------------- 환경
def iso_probe(text):
    """fromisoformat 한 번 → 'aware' | 'naive' | 'fail'."""
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return 'fail'
    return 'aware' if parsed.tzinfo else 'naive'


def _module_found(name):
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _module_usable(name):
    """실제로 import 해 본다. ImportError 외에 ABI 불일치 등도 '사용 불가'로 취급하고, 그때 나오는 경고 출력은 버린다."""
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            __import__(name)
        return True
    except Exception:  # noqa
        return False


def check_env(full=False):
    """기본 실행: python·'Z' 파싱·표준 모듈·선택 패키지·쓰기 권한. full(--env): 도구 유무·프로브 4종·런타임·환경변수 존재까지."""
    v = sys.version_info
    detail = '%d.%d.%d' % (v.major, v.minor, v.micro)
    if full:
        detail += ' (%s) · match문 %s · tomllib %s' % (
            sys.executable, '가능' if v >= (3, 10) else '불가(3.10 미만 → if/elif)', '가능' if v >= (3, 11) else '불가')
    rec('python', 'PASS', detail)
    if full:
        for label, text, fix in ISO_PROBES:
            got = iso_probe(text)
            if got == 'fail':
                rec('iso:' + label, 'WARN', '%r 거부 → %s' % (text, fix))
            elif got == 'naive':
                rec('iso:' + label, 'INFO', '%r → tzinfo 없음(naive) — aware 시각과 비교하면 TypeError' % text)
            else:
                rec('iso:' + label, 'PASS', '%r → aware' % text)
    elif iso_probe('2026-10-31T10:00:00Z') == 'fail':
        rec('iso-Z-parse', 'WARN', "fromisoformat은 'Z'를 거부 → .replace('Z', '+00:00') 필요 (Py3.9)")
    else:
        rec('iso-Z-parse', 'PASS', "fromisoformat('...Z') 지원")
    missing_std = [m for m in ENV_STDLIB if not _module_found(m)]
    for mod in missing_std:
        rec('stdlib:' + mod, 'FAIL' if mod != 'zoneinfo' else 'WARN', 'import 불가')
    if full and not missing_std:
        rec('stdlib', 'PASS', ' '.join(ENV_STDLIB))
    opt = [m for m in ENV_OPTIONAL if _module_usable(m)]
    detail = ', '.join(opt) if opt else '없음(표준 라이브러리로 진행)'
    if full:
        absent = [m for m in ENV_OPTIONAL if m not in opt]
        notes = []
        heavy = [m for m in ('pandas', 'numpy') if m in absent]
        if heavy:
            notes.append('%s 없음 → 설치하지 말고 csv·sqlite3·statistics' % '·'.join(heavy))
        if 'pytest' in absent:
            notes.append('pytest 없음 → unittest')
        detail += ' / 없음: %s%s' % (', '.join(absent) or '-', (' · ' + ' · '.join(notes)) if notes else '')
    rec('optional-packages', 'INFO', detail)
    if full:
        have = {t: bool(shutil.which(t)) for t in ENV_TOOLS}
        detail = ' · '.join('%s=%s' % (t, '있음' if ok else '없음') for t, ok in have.items())
        if not have['codex']:
            detail += ' (codex 가 PATH 에 없음 → 터미널의 실행 경로 확인)'
        rec('tools', 'INFO', detail)
        try:
            free = '%.1fGB' % (shutil.disk_usage(ROOT).free / 1024 ** 3)
        except OSError:
            free = '?'
        rec('runtime', 'INFO', '%s · CPU %s · stdout %s · LANG=%s · TZ=%s · 디스크 여유 %s' % (
            platform.platform()[:40], os.cpu_count(), getattr(sys.stdout, 'encoding', None),
            os.environ.get('LANG', '') or '-', os.environ.get('TZ', '') or '미설정', free))
        rec('env-vars', 'INFO', ' · '.join('%s=%s' % (k, 'set' if os.environ.get(k) else '-') for k in ENV_VARS) + ' (값은 출력하지 않음)')
    try:
        test_path = os.path.join(ROOT, '.preflight_write_test')
        with open(test_path, 'w', encoding='utf-8') as fh:
            fh.write('x')
        os.remove(test_path)
        rec('write-permission', 'PASS', ROOT)
    except Exception as e:  # noqa
        rec('write-permission', 'FAIL', str(e))


# ---------------------------------------------------------------- 파일 검사
def check_required(paths):
    if not paths:
        rec('required-files', 'SKIP', '--require 로 필수 파일을 지정하지 않음')
        return
    for p in paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            rec('required:' + p, 'PASS', '%d bytes' % os.path.getsize(p))
        elif os.path.exists(p):
            rec('required:' + p, 'FAIL', '파일이 비어 있음')
        else:
            rec('required:' + p, 'FAIL', '없음')


def check_todo_and_secrets():
    n_files = 0
    todo_hits, secret_hits, template_hits, abs_hits = [], [], [], []
    ABS_PAT = re.compile(r'(/home/[\w-]+/|/Users/[\w-]+/|[A-Z]:\\)')
    for path in walk_text_files():
        name = os.path.basename(path)
        if name in ('preflight.py',):
            continue
        rel = os.path.relpath(path, ROOT)
        n_files += 1
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                text = fh.read()
        except Exception:
            continue
        if SECRET_PAT.search(text):
            secret_hits.append(rel)
        todo_scope = rel.split(os.sep)[0] not in TODO_SKIP_TOP
        if todo_scope and name not in ('AGENTS.md', 'RUN.md') and name.endswith(('.md', '.py', '.html')) and TODO_PAT.search(text):
            todo_hits.append(rel)
        if name in TEMPLATE_FILES and ('Status: `TEMPLATE`' in text):
            template_hits.append(name)
        if name.endswith(('.py', '.js', '.sh')) and ABS_PAT.search(text):
            abs_hits.append(rel)
    if n_files == 0:
        rec('scan', 'SKIP', '스캔한 파일 0개 — 통과로 읽지 말 것')
        return
    rec('secret-scan', 'FAIL' if secret_hits else 'PASS', ', '.join(secret_hits) if secret_hits else '%d개 파일 이상 없음' % n_files)
    rec('todo-scan', 'WARN' if todo_hits else 'PASS', ', '.join(todo_hits[:8]) if todo_hits else 'TODO/미구현 문구 없음 (work/ 제외)')
    rec('template-status', 'WARN' if template_hits else 'PASS', ('아직 TEMPLATE 상태: ' + ', '.join(template_hits)) if template_hits else 'ACTIVE/FROZEN')
    rec('abs-path', 'WARN' if abs_hits else 'PASS', ('절대경로 하드코딩: ' + ', '.join(abs_hits[:5])) if abs_hits else '없음')


# ---------------------------------------------------------------- 동결 복구본
def _tests_hashes(tests_dir='tests'):
    import hashlib
    out = {}
    if not os.path.isdir(tests_dir):
        return out
    for dirpath, dirnames, filenames in os.walk(tests_dir):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for fn in sorted(filenames):
            if fn.endswith('.py'):
                p = os.path.join(dirpath, fn)
                with open(p, 'rb') as fh:
                    out[p.replace(os.sep, '/')] = hashlib.sha256(fh.read()).hexdigest()
    return out


def freeze_numbers():
    """.tmp/freeze_N/ 의 N 목록(오름차순)."""
    base = os.path.join(ROOT, FREEZE_PARENT)
    if not os.path.isdir(base):
        return []
    nums = []
    for d in os.listdir(base):
        m = FREEZE_RE.match(d)
        if m and os.path.isdir(os.path.join(base, d)):
            nums.append(int(m.group(1)))
    return sorted(nums)


def freeze_rel(n):
    return '%s/freeze_%d' % (FREEZE_PARENT, n)


def freeze_snapshot(tests_dir='tests'):
    """동결 복구본(스냅샷 금지의 유일한 예외): 제출 대상 파일을 새 번호의 .tmp/freeze_N/ 에 복사하고 tests/ 해시를 기록한다.
    이전 복구본은 지우지 않는다. work/ 는 포함, .tmp/·.agents/·data/·out/debug 는 제외."""
    nums = freeze_numbers()
    n = (nums[-1] + 1) if nums else 1
    target = os.path.join(ROOT, FREEZE_PARENT, 'freeze_%d' % n)
    copied = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT)
        dirnames[:] = [d for d in dirnames if d not in FREEZE_SKIP]
        if os.path.normpath(rel_dir).split(os.sep)[:2] == ['out', 'debug']:
            continue
        for fn in filenames:
            if fn.endswith(('.pyc', '.pdf')):
                continue
            src = os.path.join(dirpath, fn)
            dst = os.path.join(target, os.path.relpath(src, ROOT))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    os.makedirs(target, exist_ok=True)
    hashes = _tests_hashes(tests_dir)
    with open(os.path.join(target, FREEZE_META), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump({'frozen_at': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'tests': hashes}, fh, ensure_ascii=False, indent=1)
    rec('freeze', 'PASS', '%d개 파일 → %s/ (tests 해시 %d개, 이전 복구본 %d개 유지)' % (copied, freeze_rel(n), len(hashes), len(nums)))


def check_freeze(tests_dir='tests'):
    """가장 최근 동결 이후 tests/ 가 바뀌었으면 WARN(테스트 약화 감지). 동결 기록이 없으면 INFO 성격의 PASS."""
    nums = freeze_numbers()
    meta = os.path.join(ROOT, FREEZE_PARENT, 'freeze_%d' % nums[-1], FREEZE_META) if nums else ''
    if not meta or not os.path.exists(meta):
        rec('freeze-tests', 'PASS', '동결 기록 없음(.tmp/freeze_N/ 없음 — 사람이 --freeze 로 만든다)')
        return
    label = freeze_rel(nums[-1])
    with open(meta, encoding='utf-8') as fh:
        frozen = json.load(fh).get('tests', {})
    now_h = _tests_hashes(tests_dir)
    changed = sorted(p for p in frozen if p in now_h and now_h[p] != frozen[p])
    removed = sorted(p for p in frozen if p not in now_h)
    added = sorted(p for p in now_h if p not in frozen)
    if changed or removed:
        rec('freeze-tests', 'WARN', '%s 이후 tests 변경: %s → DECISIONS 에 승인 기록이 있어야 함' % (
            label, ', '.join([p + '(수정)' for p in changed] + [p + '(삭제)' for p in removed])))
    else:
        rec('freeze-tests', 'PASS', '%s 이후 tests 변경 없음%s' % (label, (' (+신규 %d)' % len(added)) if added else ''))


# ---------------------------------------------------------------- 위임 검사
def _import_sibling(name):
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    return __import__(name)


def check_debug_dir():
    """out/debug 정책(AGENTS.md 4절): 금지 패턴만 WARN, 폴더당 5 초과는 상세에만. 판정 로직은 scripts/debug_dir.py 하나에 둔다."""
    try:
        debug_dir = _import_sibling('debug_dir')
    except ImportError:
        rec('debug-dir', 'SKIP', 'scripts/debug_dir.py 를 불러올 수 없음 — 같은 폴더에 있는지 확인')
        return
    info = debug_dir.scan(ROOT)
    if not info['exists']:
        rec('debug-dir', 'PASS', 'out/debug 없음 (단계 폴더는 python3 scripts/debug_dir.py NN_단계명 으로 만든다)')
        return
    n_stage = sum(1 for r in info['rows'] if r[0] != '(루트)')
    if info['forbidden']:
        reasons = sorted({reason for _, reason in info['forbidden']})
        rec('debug-dir', 'WARN', '금지 패턴 %d건(%s) → python3 scripts/debug_dir.py --check 로 확인 후 정리' % (
            len(info['forbidden']), ', '.join(reasons)))
        return
    detail = '%d폴더 %d파일, 금지 패턴 없음' % (n_stage, info['total'])
    if info['over']:
        detail += ' · 폴더당 %d 초과(정리 권장): %s' % (debug_dir.MAX_PER_DIR, ', '.join(info['over'][:3]))
    rec('debug-dir', 'PASS', detail)


def check_docstrings():
    """과제 코드 함수 설명문(입력·출력 줄) 검사 — 빠지면 WARN(AGENTS.md 4절). 판정 로직은 scripts/docmap.py 하나에 둔다."""
    try:
        docmap = _import_sibling('docmap')
    except ImportError:
        rec('docstring', 'SKIP', 'scripts/docmap.py 를 불러올 수 없음 — 같은 폴더에 있는지 확인')
        return
    data = docmap.build(ROOT)
    if not data['files']:
        rec('docstring', 'SKIP', '과제 코드 없음(하네스 폴더 제외)')
        return
    probs = docmap.problem_lines(data)
    if probs:
        rec('docstring', 'WARN', '%d건: %s → python3 scripts/docmap.py --check' % (len(probs), '; '.join(probs[:4])))
    else:
        rec('docstring', 'PASS', '함수 %d개 모두 입력·출력 줄 있음' % data['n_functions'])
    if data['long_functions'] or data['long_files']:
        rec('code-size', 'INFO', '긴 함수(%d줄 초과) %d개 · 긴 파일(%d줄 초과) %d개: %s' % (
            docmap.LONG_FUNC, len(data['long_functions']), docmap.LONG_FILE, len(data['long_files']),
            ', '.join((data['long_files'] + data['long_functions'])[:4])))


def check_compile():
    dirs = [d for d in ('src', 'scripts', 'tests', 'app') if os.path.isdir(os.path.join(ROOT, d))]
    dirs += sorted(d for d in os.listdir(ROOT) if d not in dirs and d not in SKIP_DIRS
                   and os.path.isfile(os.path.join(ROOT, d, '__init__.py')))  # 과제 패키지(scaffold 의 core/ 등)
    top = [f for f in os.listdir(ROOT) if f.endswith('.py')]
    ok = True
    for d in dirs:
        if not compileall.compile_dir(os.path.join(ROOT, d), quiet=1, force=True):
            ok = False
    for f in top:
        if not compileall.compile_file(os.path.join(ROOT, f), quiet=1, force=True):
            ok = False
    rec('compile', 'PASS' if ok else 'FAIL', ', '.join(dirs + top) or '검사 대상 없음')


def run_smoke(cmd):
    if not cmd:
        rec('smoke', 'SKIP', '--smoke "<실행 명령>" 미지정')
        return
    try:
        done = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, encoding='utf-8', errors='replace')
    except subprocess.SubprocessError as e:
        rec('smoke', 'FAIL', str(e))
        return
    out = (done.stdout or '').strip()
    rec('smoke', 'PASS' if done.returncode == 0 and out else 'FAIL', 'exit %d, 출력 %d자' % (done.returncode, len(out)))


def _run_suite(suite):
    with open(os.devnull, 'w', encoding='utf-8', errors='replace') as sink:
        return unittest.TextTestRunner(verbosity=0, stream=sink).run(suite)


def run_tests(test_dir):
    if not os.path.isdir(test_dir):
        rec('tests', 'SKIP', '%s 폴더 없음' % test_dir)
        return
    suite = unittest.TestLoader().discover(test_dir, pattern='test*.py', top_level_dir=ROOT)
    n = suite.countTestCases()
    if n == 0:
        rec('tests', 'SKIP', '발견된 테스트 0개 — 통과로 읽지 말 것')
        return
    res = _run_suite(suite)
    nskip = len(res.skipped)
    nfail = len(res.failures) + len(res.errors)
    if n == nskip:
        rec('tests', 'FAIL', '전부 SKIP(%d) — 검증된 것 없음' % n)
    elif nfail:
        first = (res.failures or res.errors)[0][0].id()
        rec('tests', 'FAIL', '%d run, %d fail/error, %d skip — 첫 실패: %s (python3 -m unittest -v 로 상세)' % (n, nfail, nskip, first))
    else:
        rec('tests', 'PASS', '%d run, 0 fail, %d skip (과제 테스트 = README 테스트 수)' % (n, nskip))


def run_harness_tests(test_dir):
    """하네스 도구 테스트(scripts/tests). --harness-tests 를 줄 때만. 실패는 WARN — README 테스트 수에 넣지 않는다."""
    if not test_dir:
        rec('harness-tests', 'SKIP', '기본 생략 (--harness-tests 를 줄 때만 실행)')
        return
    if not os.path.isdir(test_dir):
        rec('harness-tests', 'SKIP', '%s 폴더 없음' % test_dir)
        return
    top = os.path.abspath(test_dir)
    suite = unittest.TestLoader().discover(top, pattern='test*.py', top_level_dir=top)
    n = suite.countTestCases()
    if n == 0:
        rec('harness-tests', 'SKIP', '발견된 테스트 0개')
        return
    res = _run_suite(suite)
    nfail = len(res.failures) + len(res.errors)
    note = '하네스 도구 점검 — README 테스트 수에 넣지 않는다'
    if nfail:
        first = (res.failures or res.errors)[0][0].id()
        rec('harness-tests', 'WARN', '%d run, %d fail/error — 첫 실패: %s (%s)' % (n, nfail, first, note))
    else:
        rec('harness-tests', 'PASS', '%d run, 0 fail, %d skip (%s)' % (n, len(res.skipped), note))


def print_results():
    print('%-28s %-5s %s' % ('CHECK', 'STATUS', 'DETAIL'))
    print('-' * 80)
    for name, status, detail in results:
        print('%-28s %-5s %s' % (name, status, detail))
    print('-' * 80)


def main():
    ap = argparse.ArgumentParser(description='제출 직전 점검 (표준 라이브러리만). 판정 숫자는 정답 증명이 아니다.')
    ap.add_argument('--require', nargs='*', default=[], help='필수 제출 파일 경로')
    ap.add_argument('--tests', default='tests', help='과제 테스트 폴더')
    ap.add_argument('--harness-tests', nargs='?', const=os.path.join('scripts', 'tests'), default=None, metavar='DIR',
                    help='하네스 도구 테스트도 실행(기본 생략). 폴더를 생략하면 scripts/tests')
    ap.add_argument('--smoke', default='', help='진입점 실행 명령 (exit 0 + 출력 있어야 PASS)')
    ap.add_argument('--env', action='store_true', help='실행 환경만 점검(python·도구 유무·모듈·fromisoformat 프로브) 후 종료')
    ap.add_argument('--freeze', action='store_true', help='복구본 .tmp/freeze_N/(번호 증가) + tests 해시 기록 후 종료. 사람만 실행')
    ap.add_argument('--check-freeze', action='store_true', help='가장 최근 동결 이후 tests/ 변경 여부만 검사')
    args = ap.parse_args()
    if args.env:
        check_env(full=True)
        print_results()
        fails = [r for r in results if r[1] == 'FAIL']
        print('RESULT: exit %d — 환경 점검%s' % (1 if fails else 0, (' FAIL %d건' % len(fails)) if fails else ' (WARN 은 PRD 8 환경에 옮길 것)'))
        sys.exit(1 if fails else 0)
    if args.freeze or args.check_freeze:
        if args.freeze:
            freeze_snapshot(args.tests)
        check_freeze(args.tests)
        for name, status, detail in results:
            print('%-28s %-5s %s' % (name, status, detail))
        sys.exit(0 if all(r[1] != 'FAIL' for r in results) else 1)
    check_env()
    check_required(args.require)
    check_todo_and_secrets()
    check_freeze(args.tests)
    check_debug_dir()
    check_docstrings()
    check_compile()
    run_tests(args.tests)
    run_harness_tests(args.harness_tests)
    run_smoke(args.smoke)
    print_results()
    checked = [r for r in results if r[1] in ('PASS', 'FAIL', 'WARN')]
    fails = [r for r in results if r[1] == 'FAIL']
    if not checked:
        print('RESULT: exit 2 — 검사한 항목이 0개입니다. 통과가 아닙니다.')
        sys.exit(2)
    if fails:
        print('RESULT: exit 1 — FAIL %d건' % len(fails))
        sys.exit(1)
    print('RESULT: exit 0 — 검사 항목 모두 통과 (정답 증명은 아님: 업무 규칙은 테스트가 답한다)')
    sys.exit(0)


if __name__ == '__main__':
    main()
