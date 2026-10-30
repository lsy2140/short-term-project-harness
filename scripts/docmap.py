#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docmap.py — 과제 코드의 함수 지도와 함수 설명문(docstring) 검사 (표준 라이브러리, Python 3.9)

사용:
  python3 scripts/docmap.py              # 함수 지도: 파일 → 함수(줄 범위·길이) → 설명 첫 줄 · 규칙 줄
  python3 scripts/docmap.py --check      # 설명문 없음 / 입력·출력 줄 없음만 출력, 있으면 exit 1
  python3 scripts/docmap.py --json       # 같은 내용을 JSON 으로
  python3 scripts/docmap.py run.py core  # 대상 파일·폴더 지정(기본: 작업 폴더의 과제 코드 전부)

과제 코드 = 작업 폴더의 .py 중 하네스·데이터·출력 폴더를 뺀 것
  (scripts · tests · design-kit · docs · decisions · data · out · screenshots · submission · 점으로 시작하는 폴더).
검사 대상 함수 = 모듈 최상위 함수와 클래스 메서드(던더 메서드·함수 안의 함수는 제외).
설명문 형식(AGENTS.md 4절): 첫 줄 요약 + `입력:` 줄 + `출력:` 줄 (+ 선택 `규칙:` `실패:` `테스트:`).
긴 함수(40줄 초과)·긴 파일(300줄 초과)은 지도에 표시만 하고 exit 에는 영향이 없다.

exit 0 문제 없음(지도 출력 포함) / 1 --check 에서 설명문 문제 있음 / 2 과제 코드 없음
"""
import argparse
import ast
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

EXCLUDE_DIRS = {'scripts', 'tests', 'design-kit', 'docs', 'decisions', 'data', 'out', 'screenshots',
                'submission', '__pycache__', 'node_modules', 'venv', 'LICENSES'}
INPUT_RE = re.compile(r'^\s*(입력|input|inputs|args?|arguments|parameters)\s*[:：]', re.I | re.M)
OUTPUT_RE = re.compile(r'^\s*(출력|output|outputs|returns?|반환)\s*[:：]', re.I | re.M)
RULE_RE = re.compile(r'^\s*(규칙|rule)\s*[:：]\s*(.*)$', re.I | re.M)
LONG_FUNC = 40
LONG_FILE = 300


def find_task_files(root, targets=None):
    """검사할 과제 코드 파일을 찾는다.

    입력: root — 작업 폴더, targets — 지정한 파일·폴더 목록(없으면 root 전체에서 과제 코드만)
    출력: root 기준 상대 경로 목록(정렬)
    """
    found = []
    bases = targets or ['.']
    for base in bases:
        path = os.path.join(root, base)
        if os.path.isfile(path):
            if path.endswith('.py'):
                found.append(os.path.relpath(path, root))
            continue
        for cur, dirs, files in os.walk(path):
            rel = os.path.relpath(cur, root)
            top = rel.split(os.sep)[0]
            if rel != '.' and (top in EXCLUDE_DIRS or top.startswith('.')):
                dirs[:] = []
                continue
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in EXCLUDE_DIRS)
            for f in sorted(files):
                if f.endswith('.py'):
                    found.append(os.path.normpath(os.path.join(rel, f)))
    return sorted(set(found))


def _functions(tree):
    """모듈 최상위 함수와 클래스 메서드를 (함수 노드, 클래스 이름) 으로 돌려준다.

    입력: tree — ast.parse 결과
    출력: (노드, 클래스 이름 또는 None) 목록 — 함수 안의 함수는 포함하지 않는다
    """
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node, None))
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((sub, node.name))
    return out


def scan_file(root, rel):
    """파일 하나의 함수와 설명문 상태를 읽는다.

    입력: root — 작업 폴더, rel — 상대 경로
    출력: {'file', 'lines', 'error', 'functions': [{'name', 'line', 'end', 'length', 'summary', 'rule', 'problems'}]}
    실패: 문법 오류는 예외 대신 'error' 에 메시지를 담는다
    """
    with io.open(os.path.join(root, rel), encoding='utf-8', errors='replace') as fh:
        src = fh.read()
    info = {'file': rel.replace(os.sep, '/'), 'lines': src.count('\n') + 1, 'error': '', 'functions': []}
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        info['error'] = '문법 오류 %s:%s' % (e.lineno, e.msg)
        return info
    for node, cls in _functions(tree):
        if node.name.startswith('__') and node.name.endswith('__'):
            continue
        doc = ast.get_docstring(node) or ''
        problems = []
        if not doc:
            problems.append('설명문 없음')
        else:
            if not INPUT_RE.search(doc):
                problems.append('입력: 줄 없음')
            if not OUTPUT_RE.search(doc):
                problems.append('출력: 줄 없음')
        end = getattr(node, 'end_lineno', node.lineno)
        rule = RULE_RE.search(doc)
        info['functions'].append({
            'name': ('%s.%s' % (cls, node.name)) if cls else node.name,
            'line': node.lineno, 'end': end, 'length': end - node.lineno + 1,
            'summary': doc.strip().splitlines()[0] if doc.strip() else '',
            'rule': rule.group(2).strip() if rule else '',
            'problems': problems,
        })
    return info


def build(root, targets=None):
    """과제 코드 전체를 읽어 지도와 요약 숫자를 만든다.

    입력: root — 작업 폴더, targets — 대상 파일·폴더(없으면 전부)
    출력: {'files': [...scan_file 결과], 'n_functions', 'n_problems', 'long_functions', 'long_files'}
    """
    files = [scan_file(root, rel) for rel in find_task_files(root, targets)]
    funcs = [(f['file'], fn) for f in files for fn in f['functions']]
    return {
        'files': files,
        'n_functions': len(funcs),
        'n_problems': sum(1 for _, fn in funcs if fn['problems']) + sum(1 for f in files if f['error']),
        'long_functions': ['%s:%d %s(%d줄)' % (p, fn['line'], fn['name'], fn['length']) for p, fn in funcs if fn['length'] > LONG_FUNC],
        'long_files': ['%s(%d줄)' % (f['file'], f['lines']) for f in files if f['lines'] > LONG_FILE],
    }


def problem_lines(data):
    """설명문 문제를 사람이 읽을 줄로 만든다.

    입력: data — build() 결과
    출력: '파일:줄 함수 — 문제' 문자열 목록
    """
    out = []
    for f in data['files']:
        if f['error']:
            out.append('%s — %s' % (f['file'], f['error']))
        for fn in f['functions']:
            if fn['problems']:
                out.append('%s:%d %s — %s' % (f['file'], fn['line'], fn['name'], ', '.join(fn['problems'])))
    return out


def render_map(data):
    """함수 지도를 텍스트로 만든다.

    입력: data — build() 결과
    출력: 여러 줄 문자열(파일마다 함수 줄 범위·설명 첫 줄·규칙, 문제 표시)
    """
    lines = []
    for f in data['files']:
        mark = '  ← 긴 파일' if f['lines'] > LONG_FILE else ''
        lines.append('%s (%d줄)%s' % (f['file'], f['lines'], mark))
        if f['error']:
            lines.append('  ! %s' % f['error'])
        for fn in f['functions']:
            flag = ' ← %s' % ', '.join(fn['problems']) if fn['problems'] else ''
            long_ = ' ← 긴 함수' if fn['length'] > LONG_FUNC else ''
            lines.append('  L%d-%d %s (%d줄) %s%s%s' % (fn['line'], fn['end'], fn['name'], fn['length'], fn['summary'], flag, long_))
            if fn['rule']:
                lines.append('      규칙: %s' % fn['rule'])
    lines.append('-' * 60)
    lines.append('함수 %d개 · 설명문 문제 %d건 · 긴 함수 %d개 · 긴 파일 %d개' % (
        data['n_functions'], data['n_problems'], len(data['long_functions']), len(data['long_files'])))
    return '\n'.join(lines)


def main(argv=None):
    """명령행 진입점.

    입력: argv — 명령행 인자(None 이면 sys.argv)
    출력: 종료 코드 0(문제 없음·지도) / 1(--check 문제 있음) / 2(과제 코드 없음)
    """
    ap = argparse.ArgumentParser(description='과제 코드 함수 지도와 설명문 검사')
    ap.add_argument('targets', nargs='*', help='대상 파일·폴더(기본: 과제 코드 전부)')
    ap.add_argument('--root', default='.', help='작업 폴더(기본: 현재 폴더)')
    ap.add_argument('--check', action='store_true', help='설명문 문제만 출력하고 있으면 exit 1')
    ap.add_argument('--json', action='store_true', help='JSON 출력')
    args = ap.parse_args(argv)
    data = build(args.root, args.targets or None)
    if not data['files']:
        print('과제 코드 없음 — 검사할 .py 가 없습니다(하네스 폴더는 제외).', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1 if (args.check and data['n_problems']) else 0
    if args.check:
        probs = problem_lines(data)
        if probs:
            print('설명문 문제 %d건 (형식: 첫 줄 요약 + 입력: + 출력:, AGENTS.md 4절)' % len(probs))
            for p in probs:
                print('  ' + p)
            return 1
        print('설명문 OK — 함수 %d개 모두 입력·출력 줄 있음' % data['n_functions'])
        return 0
    print(render_map(data))
    return 0


if __name__ == '__main__':
    sys.exit(main())
