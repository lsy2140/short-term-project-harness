#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_contract.py — 출력이 "계약"을 지켰는지 입력만 보고 다시 계산해 대조하는 독립 검사기 (숨은 테스트 시뮬레이터).
표준 라이브러리, Python 3.9. 내가 쓴 단위 테스트는 내가 놓친 규칙을 잡지 못한다. 이 스크립트는 입력과 출력만 보고 규칙을 다시 계산한다.

과제를 받은 뒤 Codex에게: "scripts/check_contract.py 의 '과제마다 바꾸는 부분'(INPUTS/OUTPUT/RUN_CMD/REQUIRED_COLUMNS/KEY_COLUMNS/
SORT_KEYS/RULES/recompute_expected/METAMORPHIC)을 이 과제 규칙으로 채워. 테스트와 독립적으로 재계산해. 종료 코드 0/1/2를 지켜."

네 층
  S 구조: 필수 열/키·순서, 허용값, 중복 키, 정렬 계약
  B 대조: 입력에서 규칙을 독립 재계산 → 출력과 키 단위 비교 (누락·초과·값 불일치)
  X 실행: RUN_CMD 를 두 번 돌려 출력 해시 동일(결정성), 입력 파일 해시 불변, 종료 코드 0
  M 메타모픽: 입력 변형(행 셔플 / 기준일 이후 행 제거 / 모델 응답 비우기) 후 재실행해도 출력이 같아야 함, 출력 전체에 민감 문자열 없음
     가드: 변형 전에 빈 폴더를 INPUT_DIR 로 1회 돌린다. exit 0 에 출력까지 같으면 RUN_CMD 가 INPUT_DIR 을 안 읽는 것 → FAIL M-noop
     (변형 입력을 안 읽은 '출력 동일' 이 통과로 읽히지 않게). scaffold 의 run.py 는 INPUT_DIR 을 기본 입력 폴더로 읽는다.
종료 코드: 0 위반 없음 / 1 위반 있음 / 2 검사한 것이 없음(통과로 읽지 말 것 — 출력도 RUN_CMD 의 .py 도 아직 없을 때)
"""
import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

# ------------------------------------------------------------ 과제마다 바꾸는 부분
INPUTS = ['data/<입력>.csv']                # 입력 파일 (불변성·변형 대상) — 과제 입력 경로로 바꾼다(자리표시 그대로면 M층 FAIL M-0)
OUTPUT = 'out/result.csv'                   # 출력 파일 (csv 또는 json)
RUN_CMD = [sys.executable, 'run.py']        # 출력을 만드는 명령(scaffold 입구 run.py). 변형 검사 때는 환경변수 INPUT_DIR 로 입력 폴더를 바꿔 실행한다(아래 참고)
REQUIRED_COLUMNS = ['id', 'value', 'status']
KEY_COLUMNS = ['id']
SORT_KEYS = [('status', False), ('id', False)]   # (열, 내림차순?) 정렬 계약. 비우면 검사 안 함
ALLOWED = {'status': {'OK', 'ALERT', 'REVIEW'}}  # 열 허용값
PII_PATTERNS = [r'\b\d{3}-\d{4}-\d{4}\b']        # 출력에 있으면 안 되는 문자열 패턴(전화·사번·실명 등 과제에 맞게)
METAMORPHIC = {
    'shuffle_rows': True,          # 입력 행 순서를 섞어도 출력 동일
    'drop_future_rows': {'file': 'data/<입력>.csv', 'date_col': 'timestamp', 'as_of': '2026-10-27T23:59:59'},  # 기준일 이후 행 제거해도 동일(누수) · 없으면 None
    'disable_model': None,         # 예: {'file': 'data/model_responses.json'} → {} 로 비워도 출력이 나와야 함(fallback)
}
# 변형 검사 규약: RUN_CMD 가 환경변수 INPUT_DIR(없으면 'data') 을 기본 입력 폴더로 읽어야 변형 입력으로 재실행할 수 있다.
# scaffold 의 run.py 는 `--input-dir` 기본값을 os.environ.get('INPUT_DIR') 로 둔다. M층 앞 가드가 빈 INPUT_DIR 로 1회 돌려
# 읽는지 확인한다(안 읽으면 FAIL M-noop). 프로그램이 INPUT_DIR 을 지원하지 않으면 METAMORPHIC 전부 None 으로 두고 S/B/X 만 쓴다.


def recompute_expected(inputs):
    """입력에서 규칙을 독립적으로 다시 계산한다. 반환 {key_tuple: {col: value}} 또는 None(생략)."""
    return None


RULES = [
    # (규칙 이름, 함수(row)->True 면 위반, 설명)
    ('status_allowed', lambda r: r.get('status') not in ALLOWED['status'], 'status 허용값 밖'),
]
# ------------------------------------------------------------


class Report(object):
    def __init__(self):
        self.fails, self.warns, self.infos = [], [], []

    def fail(self, code, msg):
        self.fails.append('%s: %s' % (code, msg))

    def warn(self, code, msg):
        self.warns.append('%s: %s' % (code, msg))

    def info(self, msg):
        self.infos.append(msg)

    def render(self):
        out = ['  [INFO] ' + m for m in self.infos] + ['  [WARN] ' + m for m in self.warns] + ['  [FAIL] ' + m for m in self.fails]
        return '\n'.join(out) if out else '  [OK] 위반 없음'


def read_rows(path):
    if path.endswith('.json'):
        with open(path, encoding='utf-8-sig') as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            lists = [v for v in data.values() if isinstance(v, list)]
            data = max(lists, key=len) if lists else [data]
        return [r if isinstance(r, dict) else {'value': r} for r in data]
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        h.update(fh.read())
    return h.hexdigest()


def _isnum(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def check_structure(rows, rep):
    if not rows:
        rep.fail('S00', '출력 행이 0개')
        return
    cols = list(rows[0].keys())
    for c in REQUIRED_COLUMNS:
        if c not in cols:
            rep.fail('S01', '필수 열 누락: %s' % c)
    present = [c for c in REQUIRED_COLUMNS if c in cols]
    if present != [c for c in cols if c in REQUIRED_COLUMNS]:
        rep.warn('S01b', '필수 열 순서가 계약과 다름: %s' % cols)
    seen = set()
    for i, r in enumerate(rows):
        k = tuple(str(r.get(c, '')) for c in KEY_COLUMNS)
        if k in seen:
            rep.fail('S02', '중복 키 %s (행 %d)' % (k, i + 2))
        seen.add(k)
        for name, pred, desc in RULES:
            try:
                if pred(r):
                    rep.fail('R-' + name, '%s (행 %d: %s)' % (desc, i + 2, {c: r.get(c) for c in REQUIRED_COLUMNS}))
                    break
            except Exception as e:  # noqa
                rep.warn('R-' + name, '규칙 평가 중 예외 %s (행 %d)' % (type(e).__name__, i + 2))
    if SORT_KEYS:
        def key(r):
            out = []
            for c, desc in SORT_KEYS:
                v = r.get(c)
                if _isnum(v):
                    out.append(-float(v) if desc else float(v))
                else:
                    out.append(str(v or ''))
            return tuple(out)
        try:
            ks = [key(r) for r in rows]
            if ks != sorted(ks):
                rep.fail('S03', '정렬 계약 위반: %s' % SORT_KEYS)
        except TypeError:
            rep.warn('S03', '정렬 키 타입 혼재로 검사 생략')


def check_against_input(rows, rep):
    expected = recompute_expected(INPUTS)
    if expected is None:
        rep.info('recompute_expected 가 None → B층 대조 생략 (과제 규칙을 옮기면 활성화)')
        return
    got = {tuple(str(r.get(c, '')) for c in KEY_COLUMNS): r for r in rows}
    missing = [k for k in expected if k not in got]
    extra = [k for k in got if k not in expected]
    for k in missing[:10]:
        rep.fail('B01', '기대에 있는데 출력에 없음: %s' % (k,))
    for k in extra[:10]:
        rep.fail('B02', '출력에 있는데 기대에 없음: %s' % (k,))
    n_bad = 0
    for k, exp in expected.items():
        if k in got:
            for c, v in exp.items():
                if str(got[k].get(c, '')) != str(v):
                    n_bad += 1
                    if n_bad <= 10:
                        rep.fail('B03', '%s %s: 출력 %r / 기대 %r' % (k, c, got[k].get(c), v))
    rep.info('대조: 기대 %d · 출력 %d · 누락 %d · 초과 %d · 값 불일치 %d' % (len(expected), len(got), len(missing), len(extra), n_bad))


def run_once(env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    done = subprocess.run(RUN_CMD, capture_output=True, text=True, env=env, encoding='utf-8', errors='replace')
    return done.returncode, (done.stderr or '')[-300:], (sha(OUTPUT) if os.path.exists(OUTPUT) else None)


def run_script():
    """RUN_CMD 가 가리키는 .py 파일 경로(없으면 None — 'python -m 모듈' 같은 형식은 확인하지 않는다)."""
    for part in RUN_CMD or []:
        if str(part).endswith('.py'):
            return str(part)
    return None


def check_execution(rep):
    if not RUN_CMD:
        rep.info('RUN_CMD 없음 → X층 생략')
        return None
    before = {p: sha(p) for p in INPUTS if os.path.exists(p)}
    if not before:
        rep.warn('X03', 'INPUTS 파일이 하나도 없음(%s) → 입력 불변 검사 생략. 과제 입력 경로로 채운다' % ', '.join(INPUTS[:3]))
    outs = []
    for i in range(2):
        rc, err, h = run_once()
        if rc != 0:
            rep.fail('X01', '%d번째 실행 실패 exit %d: %s' % (i + 1, rc, err))
            return None
        outs.append(h)
    if outs[0] != outs[1]:
        rep.fail('X02', '같은 입력에 다른 출력 (결정성 위반)')
    else:
        rep.info('X 결정성: 두 번 실행 출력 해시 동일')
    after = {p: sha(p) for p in INPUTS if os.path.exists(p)}
    for p in before:
        if before[p] != after.get(p):
            rep.fail('X03', '입력 파일이 변경됨: %s' % p)
    return outs[0]


def _write_rows(path, rows, header):
    if path.endswith('.json'):
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(rows, fh, ensure_ascii=False)
    else:
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=header)
            w.writeheader()
            w.writerows(rows)


def _missing_inputs(enabled):
    """M층이 읽을 입력 파일 중 없는 것. shuffle_rows 는 INPUTS 를, drop_future_rows 는 cfg['file'] 을 읽는다."""
    need = []
    for name, cfg in enabled:
        if name == 'shuffle_rows':
            need += list(INPUTS)
        elif name == 'drop_future_rows':
            need.append(cfg['file'])
    return [p for p in dict.fromkeys(need) if not os.path.isfile(p)]


def probe_input_dir(baseline_hash):
    """가드: 빈 폴더를 INPUT_DIR 로 주고 1회 실행한다. RUN_CMD 가 INPUT_DIR 을 읽으면 실패하거나 출력이 바뀐다(없어진다).
    출력: (읽음 True/False, 설명). 실행 전 출력 파일을 치워 두고 끝나면 기준 출력으로 되돌린다."""
    tmp = tempfile.mkdtemp(prefix='mm_probe_')
    backup = os.path.join(tmp, 'baseline_output')
    empty = os.path.join(tmp, 'empty_input')
    os.makedirs(empty)
    had_output = os.path.isfile(OUTPUT)
    try:
        if had_output:
            shutil.copy2(OUTPUT, backup)
            os.remove(OUTPUT)
        rc, err, h = run_once({'INPUT_DIR': empty})
    finally:
        if had_output:
            os.makedirs(os.path.dirname(OUTPUT) or '.', exist_ok=True)
            shutil.copy2(backup, OUTPUT)
        shutil.rmtree(tmp, ignore_errors=True)
    if rc == 0 and h == baseline_hash:
        return False, '빈 INPUT_DIR 로 돌려도 exit 0 · 출력 해시 동일'
    if rc != 0:
        return True, '빈 INPUT_DIR → exit %d' % rc
    return True, '빈 INPUT_DIR → 출력 %s' % ('없음' if h is None else '바뀜')


def check_metamorphic(rep, baseline_hash):
    enabled = [(name, cfg) for name, cfg in METAMORPHIC.items() if cfg]
    if not enabled:
        rep.info('M층: METAMORPHIC 이 모두 None → 생략')
        return
    if not RUN_CMD or baseline_hash is None:
        rep.info('M층: 기준 실행 없음 → 생략')
        return
    missing = _missing_inputs(enabled)
    if missing:
        rep.fail('M-0', '변형할 입력 파일 없음: %s → INPUTS·METAMORPHIC 의 file 을 과제 입력 경로로 채우거나 그 항목을 None 으로'
                 % ', '.join(missing[:3]))
        return
    reads, how = probe_input_dir(baseline_hash)
    if not reads:
        rep.fail('M-noop', 'RUN_CMD 가 INPUT_DIR 을 읽지 않음 → M층 무효(%s). 입력 폴더 기본값을 '
                 "os.environ.get('INPUT_DIR') 로 두거나(scaffold run.py 규약) METAMORPHIC 을 모두 None 으로" % how)
        return
    rep.info('M 가드: RUN_CMD 가 INPUT_DIR 을 읽음(%s)' % how)
    base_dir = os.path.dirname(INPUTS[0]) or 'data'
    for name, cfg in enabled:
        tmp = tempfile.mkdtemp(prefix='mm_')
        try:
            for f in os.listdir(base_dir):
                src = os.path.join(base_dir, f)
                if os.path.isfile(src):
                    shutil.copy(src, os.path.join(tmp, f))
            if name == 'shuffle_rows':
                for p in INPUTS:
                    rows = read_rows(p)
                    random.Random(1234).shuffle(rows)
                    _write_rows(os.path.join(tmp, os.path.basename(p)), rows, list(rows[0].keys()) if rows else [])
            elif name == 'drop_future_rows':
                p = cfg['file']
                rows = read_rows(p)
                kept = [r for r in rows if str(r.get(cfg['date_col'], '')) <= cfg['as_of']]
                _write_rows(os.path.join(tmp, os.path.basename(p)), kept, list(rows[0].keys()) if rows else [])
                rep.info('M %s: %d행 중 %d행 유지' % (name, len(rows), len(kept)))
            elif name == 'disable_model':
                with open(os.path.join(tmp, os.path.basename(cfg['file'])), 'w', encoding='utf-8') as fh:
                    fh.write('{}')
            rc, err, h = run_once({'INPUT_DIR': tmp})
            if rc != 0:
                rep.fail('M-%s' % name, '변형 입력에서 실행 실패 exit %d: %s' % (rc, err))
            elif name == 'disable_model':
                rep.info('M %s: 모델 응답 없이도 실행 성공(fallback 표시 여부는 출력에서 확인)' % name)
            elif h != baseline_hash:
                rep.fail('M-%s' % name, '변형 입력에서 출력이 달라짐 (%s)' % ('입력 순서 의존' if name == 'shuffle_rows' else '기준일 이후 데이터 누수 의심'))
            else:
                rep.info('M %s: 출력 동일' % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    # 기준 출력으로 복원
    run_once()


def check_pii(rep):
    if not os.path.exists(OUTPUT) or not PII_PATTERNS:
        return
    with open(OUTPUT, encoding='utf-8', errors='ignore') as fh:
        blob = fh.read()
    for pat in PII_PATTERNS:
        m = re.search(pat, blob)
        if m:
            rep.fail('M-pii', '출력에 민감 패턴 노출: %s … (%s)' % (m.group(0)[:12], pat))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--no-run', action='store_true', help='X·M층(실행·변형) 생략')
    a = ap.parse_args()
    rep = Report()
    checked = 0
    if os.path.exists(OUTPUT):
        rows = read_rows(OUTPUT)
        checked += 1
        check_structure(rows, rep)
        check_against_input(rows, rep)
        check_pii(rep)
    else:
        rep.warn('S-1', '출력 파일 없음: %s' % OUTPUT)
    if not a.no_run:
        script = run_script()
        if script and not os.path.exists(script):
            rep.warn('X00', 'RUN_CMD 의 %s 없음 → X·M층 생략(과제 코드를 만든 뒤 RUN_CMD 를 맞춘다)' % script)
        else:
            h = check_execution(rep)
            checked += 1
            check_metamorphic(rep, h)
    print('=== contract check ===')
    print(rep.render())
    if checked == 0:
        print('RESULT: exit 2 — 검사한 것이 없음. 통과로 읽지 말 것')
        sys.exit(2)
    print('RESULT: exit %d — 위반 %d · 경고 %d' % (1 if rep.fails else 0, len(rep.fails), len(rep.warns)))
    sys.exit(1 if rep.fails else 0)


if __name__ == '__main__':
    main()
