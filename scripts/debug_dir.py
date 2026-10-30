#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""debug_dir.py — 단계별 디버그 폴더 정책 도구 (표준 라이브러리, Python 3.9).

  python3 scripts/debug_dir.py 01_첫완주               # out/debug/01_첫완주/ 생성(있으면 그대로) + 파일 수·허용 외 이름 보고
  python3 scripts/debug_dir.py 01_첫완주 --strict      # 5파일 초과·허용 외 이름이 있으면 exit 1
  python3 scripts/debug_dir.py --check                 # out/debug 전체 표: 폴더별 파일 수·총 파일 수·금지 패턴
  python3 scripts/debug_dir.py --decisions 02_규칙_tz  # '결정:' 주석을 모아 out/debug/02_규칙_tz/decisions.txt 로 저장

한 폴더에 두는 파일은 5종까지: red.txt(먼저 본 FAIL) · green.txt · verify.json(숫자) · decisions.txt · note.md(결정이 필요했던 사항만).
금지 패턴: *_before(스냅샷 폴더·파일) · *_protected_before* · chrome_profile · data/ 와 같은 이름의 입력 복사본.
임시 파일(엣지 입력·셔플 사본·브라우저 프로필)은 .tmp/ 에 둔다. 복구본은 1차 동결 때 preflight --freeze 가 만드는 .tmp/freeze_1/ 뿐이다.

exit 0  이상 없음. 경고(폴더당 5 초과·허용 외 이름)는 stderr 에 줄만 내고 0 — --strict 면 1
exit 1  --check 에서 총 40 초과 또는 금지 패턴 발견 / 잘못된 단계 이름 / 쓰기 실패
exit 2  인자 없음(도움말)
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

DEBUG_REL = os.path.join('out', 'debug')
ALLOWED = ('red.txt', 'green.txt', 'verify.json', 'decisions.txt', 'note.md')
MAX_PER_DIR = 5
MAX_TOTAL = 40
STAGE_PAT = re.compile(r'^\d{2}_[^\\/\s]+$')
DECISION_MARK = '결정:'
DECISION_DIRS = ('src', 'scripts', 'tests', 'app')
SKIP_DIRS = {'__pycache__', '.git', '.tmp', 'node_modules', '.venv', 'venv'}
SELF = os.path.basename(__file__)


def eprint(msg):
    sys.stdout.flush()  # 표(stdout) 뒤에 경고(stderr)가 오도록 순서를 지킨다
    print(msg, file=sys.stderr)


def debug_root(root):
    return os.path.join(root, DEBUG_REL)


def validate_stage(stage):
    if not STAGE_PAT.match(stage):
        raise ValueError('단계 이름은 NN_단계명 형식(예 01_첫완주, 02_규칙_tz)이어야 한다: %r' % stage)


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
    rows: [(폴더, 파일 수, 허용 외 파일 목록, 금지 건수)] / total / forbidden: [(경로, 사유)] / over: 5 초과 폴더"""
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


def collect_decisions(root):
    """src/scripts/tests/app 아래 .py 와 최상위 .py 에서 '결정:' 이 든 줄을 (상대경로, 줄번호, 내용) 으로 모은다."""
    targets = []
    for d in DECISION_DIRS:
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        for base, dirs, files in os.walk(p):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
            for f in sorted(files):
                if f.endswith('.py'):
                    targets.append(os.path.join(base, f))
    for f in sorted(os.listdir(root)):
        if f.endswith('.py') and os.path.isfile(os.path.join(root, f)):
            targets.append(os.path.join(root, f))
    hits = []
    for path in targets:
        if os.path.basename(path) == SELF:  # 이 스크립트의 도움말·상수는 결정이 아니다
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                for i, line in enumerate(fh, 1):
                    if DECISION_MARK in line:
                        hits.append((_rel(path, root), i, line.rstrip('\r\n')))
        except OSError:
            continue
    return hits


def cmd_create(root, stage, strict):
    validate_stage(stage)
    path = os.path.join(debug_root(root), stage)
    created = not os.path.isdir(path)
    os.makedirs(path, exist_ok=True)
    files = list_files(path)
    extra = [f for f in files if f not in ALLOWED]
    rel = _rel(path, root)
    print('%s %s · 파일 %d/%d' % (rel, '생성' if created else '있음', len(files), MAX_PER_DIR))
    print('허용 파일: ' + ' '.join(ALLOWED))
    warns = []
    if len(files) > MAX_PER_DIR:
        warns.append('%s 파일 %d개 > %d — 5종 외 중간 출력은 지우거나 .tmp/ 로 옮긴다' % (rel, len(files), MAX_PER_DIR))
    if extra:
        warns.append('허용 외 파일 %d개: %s' % (len(extra), ', '.join(extra[:10])))
    for w in warns:
        eprint('경고: ' + w)
    if warns and strict:
        eprint('--strict: 경고 %d건 → exit 1' % len(warns))
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
        flag = '  <- %d 초과' % MAX_PER_DIR if n > MAX_PER_DIR else ''
        print('%-28s %5d %6d %5d%s' % (name, n, len(extra), nf, flag))
    print('-' * 64)
    n_stage = sum(1 for r in info['rows'] if r[0] != '(루트)')
    print('%-28s %5d %6s %5d   (총 파일 상한 %d)' % ('합계 %d폴더' % n_stage, info['total'], '', len(info['forbidden']), MAX_TOTAL))
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
    problems = []
    if info['total'] > MAX_TOTAL:
        problems.append('총 %d파일 > %d' % (info['total'], MAX_TOTAL))
    if info['forbidden']:
        problems.append('금지 패턴 %d건' % len(info['forbidden']))
    if problems:
        print('RESULT: exit 1 — %s → 스냅샷·복사본은 지우고(복구본은 preflight --freeze 의 .tmp/freeze_1/ 만), 임시물은 .tmp/ 로' % '; '.join(problems))
        return 1
    if strict and warns:
        print('RESULT: exit 1 — --strict: 경고 %d건' % len(warns))
        return 1
    print('RESULT: exit 0 — 총 %d파일(상한 %d), 금지 패턴 없음' % (info['total'], MAX_TOTAL))
    return 0


def cmd_decisions(root, stage):
    validate_stage(stage)
    hits = collect_decisions(root)
    path = os.path.join(debug_root(root), stage)
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, 'decisions.txt')
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        for rel, i, line in hits:
            fh.write('%s:%d:%s\n' % (rel, i, line))
    print('%s ← %r %d줄 (%s, 최상위 .py)' % (_rel(out, root), DECISION_MARK, len(hits), '/'.join(DECISION_DIRS)))
    n = len(list_files(path))
    if n > MAX_PER_DIR:
        eprint('경고: %s 파일 %d개 > %d — 5종 외 중간 출력은 지우거나 .tmp/ 로 옮긴다' % (_rel(path, root), n, MAX_PER_DIR))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', nargs='?', help='단계 폴더 이름 NN_단계명 (예 01_첫완주) → out/debug/NN_단계명/ 생성·점검')
    ap.add_argument('--check', action='store_true',
                    help='out/debug 전체 점검(폴더별 파일 수·총 파일 수·금지 패턴). 총 %d 초과 또는 금지 패턴이면 exit 1' % MAX_TOTAL)
    ap.add_argument('--decisions', metavar='NN_단계명', help="'결정:' 주석을 모아 out/debug/NN_단계명/decisions.txt 로 저장")
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
