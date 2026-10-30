#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preflight.py — 제출 직전 점검 (표준 라이브러리만, Python 3.8+)

사용:
  python3 scripts/preflight.py                      # 환경·TODO·비밀키·디버그 폴더·동결 해시·테스트
  python3 scripts/preflight.py --freeze             # 110분 1차 동결: .tmp/freeze_1/ 복구본 + tests/ 해시 기록(1회)
  python3 scripts/preflight.py --check-freeze       # 1차 동결 이후 tests/ 변경 여부만
  python3 scripts/preflight.py --require out/result.csv README.md PLAN.md   # 필수 제출 파일 확인
  python3 scripts/preflight.py --tests tests        # 과제 테스트 폴더 지정(기본 tests)
  python3 scripts/preflight.py --skip-harness       # 하네스 도구 테스트(scripts/tests) 생략

debug-dir: out/debug 가 없으면 PASS, 총 40파일 초과 또는 금지 패턴(*_before·*_protected_before*·chrome_profile·입력 복사본)이면
           WARN — python3 scripts/debug_dir.py --check 로 상세를 본다. .tmp/·out/debug 는 TODO·비밀키 스캔에서 제외한다.
tests: 과제 테스트(tests/)만 센다 — README 의 테스트 수는 이 줄이다.
harness-tests: 하네스 도구 테스트(scripts/tests). 실패해도 WARN 이고 README 테스트 수에 넣지 않는다.
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
import re
import subprocess
import sys
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

ROOT = os.getcwd()
SKIP_DIRS = {'.git', '.agents', '__pycache__', 'node_modules', '.venv', 'venv', 'docs', '9. 참고_공개저장소', '.tmp', '.archify'}
SKIP_RELDIRS = {os.path.join('out', 'debug')}  # 디버그 기록(red.txt·note.md 등)은 제출물이 아니다
TEXT_EXT = {'.py', '.md', '.txt', '.json', '.csv', '.toml', '.yaml', '.yml', '.html', '.js', '.sh'}
TODO_PAT = re.compile(r'\bTODO\b|\bFIXME\b|미구현|placeholder|XXX', re.I)
SECRET_PAT = re.compile(r'(sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|(api[_-]?key|secret|password|token)\s*[=:]\s*["\'][^"\']{6,}["\'])', re.I)
TEMPLATE_FILES = {'TASK.md', 'DECISIONS.md', 'PLAN.md', 'RUN.md', 'AGENTS.md'}

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


def check_env():
    v = sys.version_info
    rec('python', 'PASS', '%d.%d.%d' % (v.major, v.minor, v.micro))
    # 시간대 함정: naive vs aware
    s = '2026-10-31T10:00:00Z'
    try:
        dt.datetime.fromisoformat(s)
        rec('iso-Z-parse', 'PASS', "fromisoformat('...Z') 지원")
    except ValueError:
        rec('iso-Z-parse', 'WARN', "fromisoformat은 'Z'를 거부 → .replace('Z', '+00:00') 필요 (Py3.9)")
    for mod in ['csv', 'json', 'sqlite3', 'statistics', 'unittest']:
        try:
            __import__(mod)
        except ImportError:
            rec('stdlib:' + mod, 'FAIL', 'import 실패')
    opt = []
    for mod in ['pandas', 'numpy', 'pytest', 'openpyxl', 'fastapi', 'flask']:
        try:
            __import__(mod)
            opt.append(mod)
        except Exception:  # ImportError 외에 ABI 불일치 등도 '사용 불가'로 취급
            pass
    rec('optional-packages', 'INFO', ', '.join(opt) if opt else '없음(표준 라이브러리로 진행)')
    try:
        test_path = os.path.join(ROOT, '.preflight_write_test')
        with open(test_path, 'w') as fh:
            fh.write('x')
        os.remove(test_path)
        rec('write-permission', 'PASS', ROOT)
    except Exception as e:  # noqa
        rec('write-permission', 'FAIL', str(e))


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
        n_files += 1
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                text = fh.read()
        except Exception:
            continue
        if SECRET_PAT.search(text):
            secret_hits.append(os.path.relpath(path, ROOT))
        if name not in ('AGENTS.md', 'RUN.md') and name.endswith(('.md', '.py', '.html')) and TODO_PAT.search(text):
            todo_hits.append(os.path.relpath(path, ROOT))
        if name in TEMPLATE_FILES and ('Status: `TEMPLATE`' in text):
            template_hits.append(name)
        if name.endswith(('.py', '.js', '.sh')) and ABS_PAT.search(text):
            abs_hits.append(os.path.relpath(path, ROOT))
    if n_files == 0:
        rec('scan', 'SKIP', '스캔한 파일 0개 — 통과로 읽지 말 것')
        return
    rec('secret-scan', 'FAIL' if secret_hits else 'PASS', ', '.join(secret_hits) if secret_hits else '%d개 파일 이상 없음' % n_files)
    rec('todo-scan', 'WARN' if todo_hits else 'PASS', ', '.join(todo_hits[:8]) if todo_hits else 'TODO/미구현 문구 없음')
    rec('template-status', 'WARN' if template_hits else 'PASS', ('아직 TEMPLATE 상태: ' + ', '.join(template_hits)) if template_hits else 'ACTIVE/FROZEN')
    rec('abs-path', 'WARN' if abs_hits else 'PASS', ('절대경로 하드코딩: ' + ', '.join(abs_hits[:5])) if abs_hits else '없음')


FREEZE_DIR = os.path.join('.tmp', 'freeze_1')
FREEZE_SKIP = {'.tmp', '.git', '__pycache__', '.agents', 'data', 'node_modules', '.venv', 'venv', '.archify', 'debug'}  # .agents(스킬 원문)·data(입력 불변)·out/debug 제외


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


def freeze_snapshot(tests_dir='tests'):
    """1차 동결 복구본(스냅샷 금지의 유일한 예외): 제출 대상 파일을 .tmp/freeze_1/ 에 복사하고 tests/ 해시를 기록한다."""
    import shutil
    if os.path.isdir(FREEZE_DIR):
        shutil.rmtree(FREEZE_DIR)
    copied = 0
    for dirpath, dirnames, filenames in os.walk('.'):
        dirnames[:] = [d for d in dirnames if d not in FREEZE_SKIP]
        if os.path.normpath(dirpath).split(os.sep)[:2] == ['out', 'debug']:
            continue
        for fn in filenames:
            if fn.endswith(('.pyc', '.pdf')):
                continue
            src = os.path.join(dirpath, fn)
            dst = os.path.join(FREEZE_DIR, os.path.relpath(src, '.'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    with open(os.path.join(FREEZE_DIR, 'tests.sha256.json'), 'w', encoding='utf-8') as fh:
        json.dump({'frozen_at': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'tests': _tests_hashes(tests_dir)}, fh, ensure_ascii=False, indent=1)
    rec('freeze', 'PASS', '%d개 파일 → %s (tests 해시 %d개)' % (copied, FREEZE_DIR, len(_tests_hashes(tests_dir))))


def check_freeze(tests_dir='tests'):
    """1차 동결 이후 tests/ 가 바뀌었으면 WARN(테스트 약화 감지). 동결 기록이 없으면 INFO 성격의 PASS."""
    meta = os.path.join(FREEZE_DIR, 'tests.sha256.json')
    if not os.path.exists(meta):
        rec('freeze-tests', 'PASS', '1차 동결 기록 없음(110분에 --freeze 1회)')
        return
    with open(meta, encoding='utf-8') as fh:
        frozen = json.load(fh).get('tests', {})
    now_h = _tests_hashes(tests_dir)
    changed = sorted(p for p in frozen if p in now_h and now_h[p] != frozen[p])
    removed = sorted(p for p in frozen if p not in now_h)
    added = sorted(p for p in now_h if p not in frozen)
    if changed or removed:
        rec('freeze-tests', 'WARN', '1차 동결 이후 tests 변경: ' + ', '.join([p + '(수정)' for p in changed] + [p + '(삭제)' for p in removed]) + ' → DECISIONS 에 승인 기록이 있어야 함')
    else:
        rec('freeze-tests', 'PASS', '1차 동결 이후 tests 변경 없음' + (' (+신규 %d)' % len(added) if added else ''))


def check_debug_dir():
    """out/debug 정책(AGENTS.md 4절): 총 40파일 초과 또는 금지 패턴이면 WARN. 판정 로직은 scripts/debug_dir.py 하나에 둔다."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import debug_dir
    except ImportError:
        rec('debug-dir', 'SKIP', 'scripts/debug_dir.py 를 불러올 수 없음 — 같은 폴더에 있는지 확인')
        return
    info = debug_dir.scan(ROOT)
    if not info['exists']:
        rec('debug-dir', 'PASS', 'out/debug 없음 (단계 폴더는 python3 scripts/debug_dir.py NN_단계명 으로 만든다)')
        return
    n_stage = sum(1 for r in info['rows'] if r[0] != '(루트)')
    problems = []
    if info['total'] > debug_dir.MAX_TOTAL:
        problems.append('총 %d파일 > %d' % (info['total'], debug_dir.MAX_TOTAL))
    if info['forbidden']:
        reasons = sorted({reason for _, reason in info['forbidden']})
        problems.append('금지 패턴 %d건(%s)' % (len(info['forbidden']), ', '.join(reasons)))
    if problems:
        rec('debug-dir', 'WARN', '; '.join(problems) + ' → python3 scripts/debug_dir.py --check 로 확인 후 정리')
        return
    detail = '%d폴더 %d파일 (상한 %d)' % (n_stage, info['total'], debug_dir.MAX_TOTAL)
    if info['over']:
        detail += ', 폴더당 %d 초과: %s' % (debug_dir.MAX_PER_DIR, ', '.join(info['over'][:3]))
    rec('debug-dir', 'PASS', detail)


def check_docstrings():
    """과제 코드 함수 설명문(입력·출력 줄) 검사 — 빠지면 WARN(AGENTS.md 4절). 판정 로직은 scripts/docmap.py 하나에 둔다."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import docmap
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


def run_tests(test_dir):
    if not os.path.isdir(test_dir):
        rec('tests', 'SKIP', '%s 폴더 없음' % test_dir)
        return
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern='test*.py', top_level_dir=ROOT)
    n = suite.countTestCases()
    if n == 0:
        rec('tests', 'SKIP', '발견된 테스트 0개 — 통과로 읽지 말 것')
        return
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w', encoding='utf-8', errors='replace'))
    res = runner.run(suite)
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
    """하네스 도구 테스트(scripts/tests). 실패는 WARN — 과제 결과가 아니므로 README 테스트 수에 넣지 않는다."""
    if not os.path.isdir(test_dir):
        rec('harness-tests', 'SKIP', '%s 폴더 없음' % test_dir)
        return
    top = os.path.abspath(test_dir)
    suite = unittest.TestLoader().discover(top, pattern='test*.py', top_level_dir=top)
    n = suite.countTestCases()
    if n == 0:
        rec('harness-tests', 'SKIP', '발견된 테스트 0개')
        return
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w', encoding='utf-8', errors='replace'))
    res = runner.run(suite)
    nfail = len(res.failures) + len(res.errors)
    note = '하네스 도구 점검 — README 테스트 수에 넣지 않는다'
    if nfail:
        first = (res.failures or res.errors)[0][0].id()
        rec('harness-tests', 'WARN', '%d run, %d fail/error — 첫 실패: %s (%s)' % (n, nfail, first, note))
    else:
        rec('harness-tests', 'PASS', '%d run, 0 fail, %d skip (%s)' % (n, len(res.skipped), note))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--require', nargs='*', default=[], help='필수 제출 파일 경로')
    ap.add_argument('--tests', default='tests', help='과제 테스트 폴더')
    ap.add_argument('--harness-tests', default=os.path.join('scripts', 'tests'), help='하네스 도구 테스트 폴더')
    ap.add_argument('--skip-harness', action='store_true', help='하네스 도구 테스트 생략')
    ap.add_argument('--smoke', default='', help='진입점 실행 명령 (exit 0 + 출력 있어야 PASS)')
    ap.add_argument('--freeze', action='store_true', help='1차 동결 복구본(.tmp/freeze_1/) + tests 해시 기록 후 종료')
    ap.add_argument('--check-freeze', action='store_true', help='1차 동결 이후 tests/ 변경 여부만 검사')
    args = ap.parse_args()
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
    if not args.skip_harness:
        run_harness_tests(args.harness_tests)
    run_smoke(args.smoke)
    print('%-28s %-5s %s' % ('CHECK', 'STATUS', 'DETAIL'))
    print('-' * 80)
    for name, status, detail in results:
        print('%-28s %-5s %s' % (name, status, detail))
    checked = [r for r in results if r[1] in ('PASS', 'FAIL', 'WARN')]
    fails = [r for r in results if r[1] == 'FAIL']
    print('-' * 80)
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
