#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""debug_dir.py — 단계별 디버그 폴더 정책 도구 (표준 라이브러리, Python 3.9).

  python3 scripts/debug_dir.py 01_계약                 # out/debug/01_계약/ 생성(있으면 그대로) + 파일 수·허용 외 이름 보고
  python3 scripts/debug_dir.py 01_계약 --strict        # 폴더당 5파일 초과·허용 외 이름이 있으면 exit 1
  python3 scripts/debug_dir.py --check                 # out/debug 전체 표: 폴더별 파일 수·금지 패턴
  python3 scripts/debug_dir.py --decisions 02_규칙_tz  # '결정:' 주석 목록을 out/debug/02_규칙_tz/verify.json 의 "decisions" 키에 병합
                                                       #   찾는 곳: src·scripts·tests·app·과제 패키지(__init__.py 가 있는 최상위 폴더, 예 core/)·최상위 .py

한 폴더에 두는 파일은 4종: red.txt(먼저 본 FAIL) · green.txt · verify.json(숫자 + "decisions") · note.md(결정이 필요했던 사항만).
폴더 수·총 파일 수에는 상한이 없다(단계가 늘면 폴더도 는다, 예 01_계약 … 09_동결). 폴더당 5파일 초과는 경고만 낸다.
금지 패턴: *_before(스냅샷 폴더·파일) · *_protected_before* · chrome_profile · data/ 와 같은 이름의 입력 복사본.
임시 파일(엣지 입력·셔플 사본·브라우저 프로필)은 .tmp/ 에 둔다. 복구본은 사람이 preflight --freeze 로 만드는 .tmp/freeze_N/ 뿐이다.

exit 0  이상 없음. 경고(폴더당 5 초과·허용 외 이름)는 stderr 에 줄만 내고 0 — --strict 면 1
exit 1  금지 패턴 발견 / 잘못된 단계 이름 / verify.json 이 JSON 객체가 아님 / 쓰기 실패
exit 2  인자 없음(도움말)
"""
import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

DEBUG_REL = os.path.join('out', 'debug')
ALLOWED = ('red.txt', 'green.txt', 'verify.json', 'note.md')
MAX_PER_DIR = 5
STAGE_PAT = re.compile(r'^\d{2}_[^\\/\s]+$')
DECISION_MARK = '결정:'
DECISION_KEY = 'decisions'
DECISION_DIRS = ('src', 'scripts', 'tests', 'app')
SKIP_DIRS = {'__pycache__', '.git', '.tmp', 'node_modules', '.venv', 'venv'}
# 하네스 도구(scripts/ 의 고정 파일과 scripts/tests)의 '결정:' 주석은 과제 결정이 아니다. check_contract.py 는 과제 규칙을 채우므로 센다.
HARNESS_SCRIPTS = {'status.py', 'preflight.py', 'debug_dir.py', 'decide.py', 'scaffold.py', 'docmap.py',
                   'smoke_web.py', 'eda_bootstrap.py', 'make_edge_cases.py'}
HARNESS_TEST_REL = os.path.join('scripts', 'tests')


def eprint(msg):
    sys.stdout.flush()  # 표(stdout) 뒤에 경고(stderr)가 오도록 순서를 지킨다
    print(msg, file=sys.stderr)


def debug_root(root):
    return os.path.join(root, DEBUG_REL)


def validate_stage(stage):
    if not STAGE_PAT.match(stage):
        raise ValueError('단계 이름은 NN_단계명 형식(예 01_계약, 02_규칙_tz, 09_동결)이어야 한다: %r' % stage)


def _rel(path, base):
    return os.path.relpath(path, base).replace('\\', '/')


def list_files(path):
    """path 아래 모든 파일의 상대 경로(정렬). 하위 폴더 안까지 센다."""
    out = []
    for base, dirs, files in os.walk(path):
        dirs.sort()
        for f in sorted(files):
            out.append(_rel(os.path.join(base, f), path))
    return out


def data_names(root):
    """data/ 아래 파일 이름 집합. out/debug 에 같은 이름이 있으면 입력 복사본으로 본다."""
    names = set()
    data_dir = os.path.join(root, 'data')
    if not os.path.isdir(data_dir):
        return names
    for base, dirs, files in os.walk(data_dir):
        for f in files:
            if f not in ALLOWED:
                names.add(f)
    return names


def forbidden_reason(name, is_dir, data_set):
    """이름 하나가 금지 패턴에 걸리면 사유 문자열, 아니면 ''."""
    low = name.lower().replace('-', '_')
    stem = low if is_dir else os.path.splitext(low)[0]
    if '_protected_before' in low:
        return '*_protected_before*'
    if stem.endswith('_before'):
        return '*_before'
    if 'chrome_profile' in low:
        return 'chrome_profile'
    if not is_dir and name in data_set:
        return 'data/ 입력 복사본'
    return ''


def scan(root):
    """out/debug 전체 요약.
    rows: [(폴더, 파일 수, 허용 외 파일 목록, 금지 건수)] / total / forbidden: [(경로, 사유)] / over: 폴더당 5 초과 폴더"""
    droot = debug_root(root)
    info = {'exists': os.path.isdir(droot), 'rows': [], 'total': 0, 'forbidden': [], 'over': []}
    if not info['exists']:
        return info
    data_set = data_names(root)
    for base, dirs, files in os.walk(droot):
        dirs.sort()
        rel_base = _rel(base, droot)
        prefix = '' if rel_base == '.' else rel_base + '/'
        for d in dirs:
            reason = forbidden_reason(d, True, data_set)
            if reason:
                info['forbidden'].append((prefix + d + '/', reason))
        for f in sorted(files):
            reason = forbidden_reason(f, False, data_set)
            if reason:
                info['forbidden'].append((prefix + f, reason))
    top_files, stages = [], []
    for name in sorted(os.listdir(droot)):
        if os.path.isdir(os.path.join(droot, name)):
            stages.append(name)
        else:
            top_files.append(name)
    if top_files:
        nf = sum(1 for p, _ in info['forbidden'] if '/' not in p)
        info['rows'].append(('(루트)', len(top_files), list(top_files), nf))
    for s in stages:
        files = list_files(os.path.join(droot, s))
        extra = [f for f in files if f not in ALLOWED]
        nf = sum(1 for p, _ in info['forbidden'] if p == s + '/' or p.startswith(s + '/'))
        info['rows'].append((s, len(files), extra, nf))
        if len(files) > MAX_PER_DIR:
            info['over'].append(s)
    info['total'] = sum(r[1] for r in info['rows'])
    return info


def decision_dirs(root):
    """'결정:' 주석을 찾을 폴더(있는 것만). src·scripts·tests·app 과 과제 패키지(최상위 폴더 중 __init__.py 가 있는 것,
    예 scaffold 의 core/ · --package 로 바꾼 이름) — preflight.py 의 compile 검사와 같은 규칙. 출력: 폴더 이름 목록."""
    dirs = [d for d in DECISION_DIRS if os.path.isdir(os.path.join(root, d))]
    dirs += sorted(d for d in os.listdir(root) if d not in dirs and d not in SKIP_DIRS and not d.startswith('.')
                   and os.path.isfile(os.path.join(root, d, '__init__.py')))
    return dirs


def _decision_targets(root):
    targets = []
    for d in decision_dirs(root):
        p = os.path.join(root, d)
        for base, dirs, files in os.walk(p):
            rel_base = os.path.normpath(os.path.relpath(base, root))
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS
                             and os.path.normpath(os.path.join(rel_base, x)) != HARNESS_TEST_REL)
            for f in sorted(files):
                if not f.endswith('.py'):
                    continue
                if rel_base == 'scripts' and f in HARNESS_SCRIPTS:
                    continue
                targets.append(os.path.join(base, f))
    for f in sorted(os.listdir(root)):
        if f.endswith('.py') and os.path.isfile(os.path.join(root, f)):
            targets.append(os.path.join(root, f))
    return targets


def collect_decisions(root):
    """src/scripts/tests/app·과제 패키지(core/ 등, decision_dirs) 아래 .py 와 최상위 .py 에서 '결정:' 이 든 줄을
    (상대경로, 줄번호, 내용) 으로 모은다. 하네스 도구(scripts/ 의 고정 파일·scripts/tests)는 뺀다."""
    hits = []
    for path in _decision_targets(root):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                for i, line in enumerate(fh, 1):
                    if DECISION_MARK in line:
                        hits.append((_rel(path, root), i, line.strip()))
        except OSError:
            continue
    return hits


def merge_decisions(verify_path, lines):
    """verify.json 의 "decisions" 키를 lines 로 바꾸고 다른 키는 그대로 둔다(파일이 없으면 만든다).
    출력: 병합된 dict. verify.json 이 JSON 객체가 아니면 ValueError(파일은 건드리지 않는다)."""
    data = {}
    if os.path.exists(verify_path):
        with open(verify_path, 'r', encoding='utf-8') as fh:
            text = fh.read()
        if text.strip():
            try:
                data = json.loads(text)
            except ValueError:
                raise ValueError('%s 가 올바른 JSON 이 아니다 — 고친 뒤 다시 실행한다(덮어쓰지 않음)' % verify_path)
            if not isinstance(data, dict):
                raise ValueError('%s 의 최상위가 JSON 객체가 아니다 — 고친 뒤 다시 실행한다(덮어쓰지 않음)' % verify_path)
    data[DECISION_KEY] = list(lines)
    with open(verify_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    return data


def _warn_over(path, root, n):
    eprint('경고: %s 파일 %d개 > %d — 4종(%s) 외 중간 출력은 지우거나 .tmp/ 로 옮긴다'
           % (_rel(path, root), n, MAX_PER_DIR, ' '.join(ALLOWED)))


def cmd_create(root, stage, strict):
    validate_stage(stage)
    path = os.path.join(debug_root(root), stage)
    created = not os.path.isdir(path)
    os.makedirs(path, exist_ok=True)
    files = list_files(path)
    extra = [f for f in files if f not in ALLOWED]
    print('%s %s · 파일 %d/%d' % (_rel(path, root), '생성' if created else '있음', len(files), MAX_PER_DIR))
    print('허용 파일: ' + ' '.join(ALLOWED))
    n_warn = 0
    if len(files) > MAX_PER_DIR:
        _warn_over(path, root, len(files))
        n_warn += 1
    if extra:
        eprint('경고: 허용 외 파일 %d개: %s' % (len(extra), ', '.join(extra[:10])))
        n_warn += 1
    if n_warn and strict:
        eprint('--strict: 경고 %d건 → exit 1' % n_warn)
        return 1
    return 0


def cmd_check(root, strict):
    info = scan(root)
    if not info['exists']:
        print('out/debug 없음 — 검사 대상 0 (단계 폴더는 python3 scripts/debug_dir.py NN_단계명 으로 만든다)')
        return 0
    print('%-28s %5s %6s %5s' % ('폴더', '파일', '허용외', '금지'))
    print('-' * 64)
    for name, n, extra, nf in info['rows']:
        flag = '  <- %d 초과(경고)' % MAX_PER_DIR if n > MAX_PER_DIR else ''
        print('%-28s %5d %6d %5d%s' % (name, n, len(extra), nf, flag))
    print('-' * 64)
    n_stage = sum(1 for r in info['rows'] if r[0] != '(루트)')
    print('%-28s %5d %6s %5d' % ('합계 %d폴더' % n_stage, info['total'], '', len(info['forbidden'])))
    for p, reason in info['forbidden']:
        print('  금지: %s  (%s)' % (p, reason))
    warns = []
    for name, n, extra, nf in info['rows']:
        if extra:
            warns.append('%s 허용 외 파일 %d개: %s' % (name, len(extra), ', '.join(extra[:8])))
    if info['over']:
        warns.append('폴더당 %d 초과: %s' % (MAX_PER_DIR, ', '.join(info['over'])))
    for w in warns:
        eprint('경고: ' + w)
    if info['forbidden']:
        print('RESULT: exit 1 — 금지 패턴 %d건 → 스냅샷·복사본은 지우고(복구본은 preflight --freeze 의 .tmp/freeze_N/ 만), 임시물은 .tmp/ 로'
              % len(info['forbidden']))
        return 1
    if strict and warns:
        print('RESULT: exit 1 — --strict: 경고 %d건' % len(warns))
        return 1
    print('RESULT: exit 0 — %d폴더 %d파일, 금지 패턴 없음%s'
          % (n_stage, info['total'], (' (경고 %d건은 stderr)' % len(warns)) if warns else ''))
    return 0


def cmd_decisions(root, stage):
    validate_stage(stage)
    hits = collect_decisions(root)
    path = os.path.join(debug_root(root), stage)
    os.makedirs(path, exist_ok=True)
    verify = os.path.join(path, 'verify.json')
    merge_decisions(verify, ['%s:%d:%s' % (rel, i, line) for rel, i, line in hits])
    scanned = decision_dirs(root)
    print('%s ← "%s" 키 %d줄 (%r 주석을 찾은 곳: %s최상위 .py · 하네스 도구 제외)'
          % (_rel(verify, root), DECISION_KEY, len(hits), DECISION_MARK,
             ''.join(d + '/ · ' for d in scanned)))
    n = len(list_files(path))
    if n > MAX_PER_DIR:
        _warn_over(path, root, n)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', nargs='?', help='단계 폴더 이름 NN_단계명 (예 01_계약) → out/debug/NN_단계명/ 생성·점검')
    ap.add_argument('--check', action='store_true',
                    help='out/debug 전체 점검(폴더별 파일 수·금지 패턴). 금지 패턴이 있을 때만 exit 1')
    ap.add_argument('--decisions', metavar='NN_단계명',
                    help="'결정:' 주석 목록을 out/debug/NN_단계명/verify.json 의 \"decisions\" 키에 병합(없으면 생성)")
    ap.add_argument('--strict', action='store_true', help='경고(폴더당 %d 초과·허용 외 이름)도 exit 1' % MAX_PER_DIR)
    ap.add_argument('--root', default='.', help='과제 폴더(기본 현재 폴더)')
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    try:
        if args.check:
            return cmd_check(root, args.strict)
        if args.decisions:
            return cmd_decisions(root, args.decisions)
        if args.stage:
            return cmd_create(root, args.stage, args.strict)
    except ValueError as e:
        eprint('오류: %s' % e)
        return 1
    except OSError as e:
        eprint('오류: %s → 경로·쓰기 권한을 확인한다' % e)
        return 1
    ap.print_help(sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
