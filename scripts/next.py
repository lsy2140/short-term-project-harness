#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""next.py — 지금 구간·규칙 진행·다음 추천 3개·대기 중 할 일 (AGENTS.md 7절 보고 꼬리 3줄).

사용:
  python3 scripts/next.py                    # TASK.md 머리의 `시작: HH:MM` 을 읽는다
  python3 scripts/next.py --start 09:00      # TASK.md 에 시작 시각이 없을 때
  python3 scripts/next.py --tests 5/7        # unittest 결과(PASS/전체)를 직접 알려줄 때
  python3 scripts/next.py --json             # 같은 내용을 JSON 으로
  python3 scripts/next.py --now 10:25        # 재현·테스트용 현재 시각

입력(모두 가벼운 읽기, 테스트를 돌리지 않는다):
  TASK.md 머리 20줄의 `시작: HH:MM` · PLAN.md 4번 규칙표(상태 열의 PASS/FAIL/NOT_RUN) ·
  out/debug/*/green.txt|red.txt 유무 · out/debug 최신 파일 시각 (없으면 '기록 없음')
출력 3줄:
  지금: ⑤ 규칙 3/7 · 경과 74분 · 1차 동결까지 36분 · 마지막 기록 12분 전
  다음 추천: (1) … (2) … (3) …
  대기 중 할 일(사람): …
구간 경계는 이 파일의 PHASES(RUN.md 구간표와 같은 경계)이고, 대기 중 문구는 RUN.md 구간표의 마지막 열과 글자 그대로 같다
(tests/test_next.py 가 둘 다 대조한다).
exit 0: 출력함(시작 시각이 없어도 안내 후 0) / exit 2: 인자 형식 오류
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

# 구간표(경과 분 기준). RUN.md 구간표의 첫 열과 같은 경계다.
PHASES = [
    (0, 10, '① 읽기 — README·파일·형식 (코드 금지)'),
    (10, 30, '② 계약·인터뷰 — TASK.md, 담당자 질문, 합의문'),
    (30, 63, '④ 첫 완주 — 가장 작은 end-to-end + 첫 기록(out/debug/01_첫완주)'),
    (63, 110, '⑤ 규칙·검증 — 규칙 1개 = 테스트 1개, 엣지케이스, 디버그 폴더 기록 (80분 이후 새 접근 금지)'),
    (110, 120, '1차 동결 — 지금 제출해도 되는 상태: preflight 0 · README 명령 실행 · preflight --freeze 복구본'),
    (120, 130, '⑤ 규칙·검증 계속 — 설명할 수 있는 것만 추가'),
    (130, 144, '점검 — preflight FAIL 0, 심사자 시뮬레이션, PLAN 초안'),
    (144, 165, '⑥ 동결 — 문서 정리(증거 좌표), HANDOFF.md, 한계 기록, /review'),
    (165, 170, '최종 — 증거 좌표 재점검, preflight 재실행, 저장 상태 확인'),
    (170, 999, '제출 — 제출하고 문제풀기 → 확정'),
]


def phase_of(elapsed):
    for a, b, name in PHASES:
        if a <= elapsed < b:
            return name, b
    return PHASES[-1][2], 999


# RUN.md 구간표의 '대기 중 사람이 할 일' 열. 키는 RUN.md 첫 열(경과)과 같은 글자(–는 U+2013).
# 문구를 고칠 때는 RUN.md 를 먼저 고치고 여기를 맞춘다 — tests/test_next.py 가 불일치를 FAIL 로 잡는다.
WAITING = {
    '0': 'README 두 번째 정독, 제출 파일명·형식 메모',
    '0–10': 'P0 체크 표시, eda_summary 를 내 말로 3줄 번역',
    '10–30': '담당자 창 왕복, 되묻기 후보 2개 준비, 합의문을 소리 내어 읽기',
    '30–63': '`decisions/pending.md` 답하기(`decide.py`), 보고서 세션에 `$stage-report 1` 요청 → `out/report/` 확인, 담당자 추가 질문 1개',
    '63–110': "DECISIONS 4번·debug 폴더 note.md 가 '무엇·왜'인지 확인, 보고서 세션에 끝난 단계 묶음(예 1-3) 보고서 요청 → 차트·숫자·샘플 검증, HUMAN_CHECK 화면, 서술형 답변 ① 초안",
    '110–120': '제출 체크 앞 절반 표시, 서술형 답변 ② 초안',
    '120–130': '서술형 답변 ③ 초안, `decisions/` 미답 항목 0 확인',
    '130–144': '심사 결과에서 미충족 2개를 내 말로 메모',
    '144–165': 'README 데모 순서를 직접 실행, 설명 못 하는 코드 찾기',
    '165–170': '제출 버튼 위치 재확인',
    '170': '',
}

# 고정 (1) 문구 — 100~120분과 144분 이후 (AGENTS.md 7절)
FIRST_FREEZE = ('1차 동결: preflight exit 0 · check_contract.py · README 실행 명령 실제 실행 · TASK 가정 동기화 '
                '→ `python3 scripts/preflight.py --freeze`(복구본 .tmp/freeze_1/ · tests 해시)')
FINAL_FREEZE = '기능 추가 중단 · 문서 정리: README·PLAN·DECISIONS 주장마다 증거 좌표, HANDOFF.md, 한계·안 한 것 기록'
NO_NEW_APPROACH = '새 접근 금지(80분 이후: 라이브러리·구조 변경 안 함)'

# 구간별 기본 추천 (RUN.md '할 일' 열 요약). 신호(FAIL·NOT_RUN·기록 경과)가 있으면 그것이 앞에 온다.
PHASE_TODO = {
    '0': ['README 정독(코드 금지) → 한 문장 목표',
          '하네스 복사 5분 이내 · TASK.md 머리에 `시작: HH:MM`',
          '보고마다 `python3 scripts/next.py` 로 지금 구간·다음 추천 확인'],
    '0–10': ['README·파일 목록·데이터 형식·제출물·평가 기준 읽기(코드 금지) · P0 10항목',
             '`python3 scripts/eda_bootstrap.py <데이터 파일>` 로 데이터 첫 파악',
             'TASK.md 1번(사실)에 제출 파일명·형식을 원문 그대로'],
    '10–30': ['TASK.md 1~5 채우기(사실·가정·열린 질문·안 할 일·완료 조건)',
              '담당자 질문 5~8개(번호, 한 주제 한 질문) 보내기 → 답변을 `답변 N:` 으로 매핑',
              'DECISIONS.md 0번 합의문 → 담당자 확인'],
    '30–63': ['가장 작은 end-to-end: 입력 → 출력 파일 생성 → 형식 확인',
              '`python3 scripts/debug_dir.py 01_첫완주` 로 첫 기록(웹 과제는 템플릿 복사 → 더미 렌더 → 미리보기 확인)',
              '`out/debug/01_첫완주/verify.json` 채우기 → 사람이 보고서 세션에 `$stage-report 1`'],
    '63–110': ['규칙 1개 = 테스트 1개: 먼저 FAIL → 구현 → PASS → 발동 건수 → 디버그 폴더 기록',
               '`python3 -m unittest -v` 와 `python3 scripts/check_contract.py` 짝으로 실행',
               'DECISIONS.md 1·5번(결정 3·깨질 입력 3·재검증 1) · 단계 폴더 verify.json 갱신'],
    '110–120': [FIRST_FREEZE,
                '`python3 scripts/preflight.py --require <필수 파일>` exit 0 확인',
                'README 실행 명령을 실제로 치고 TASK.md 가정 동기화'],
    '120–130': ['설명할 수 있는 규칙만 추가(테스트 먼저 FAIL)',
                '`decisions/pending.md` 미답 항목 0 확인(전부 사람이 답함)',
                '단계 폴더 verify.json 갱신'],
    '130–144': ['`python3 scripts/preflight.py --require <필수 파일>` FAIL 0',
                '심사자 시뮬레이션 1회(docs/judge_simulation.md, 별도 read-only 세션) → 미충족 보완',
                'PLAN.md 초안(1·2·4·5절 숫자 채우기)'],
    '144–165': [FINAL_FREEZE,
                'HANDOFF.md 작성 · 템플릿 문구 제거 · `/review`',
                '보고서 세션에 `$stage-report all` → README 데모 순서에 `out/report/index.html` 링크 · 서술형 답변 3개 문장화'],
    '165–170': ['증거 좌표 누락 재점검(README·PLAN·DECISIONS 주장마다 파일:줄·테스트·실행 명령)',
                'preflight 재실행 · 필수 파일 경로·저장 상태(저장됨) 확인',
                '필수 파일 저장 상태(저장됨) 마지막 확인'],
    '170': ['"제출하고 문제풀기" → 미리보기 → "제출물 확정하고 문제풀기"',
            'DECISIONS 5·7, TASK 8 다시 읽기',
            '서술형 답변 3개 소리 내어 읽기(docs/written_answer_prep.md)'],
}

MILESTONES = [(110, '1차 동결'), (144, '동결'), (170, '제출')]
NO_START_MSG = "시작 시각 없음 → TASK.md 머리에 '시작: HH:MM' 을 적어 주세요"
NO_START_HINT = '  (또는 python3 scripts/next.py --start HH:MM)'
STATUS_PAT = re.compile(r'\b(PASS|FAIL|NOT_RUN|HUMAN_CHECK)\b')
START_PAT = re.compile(r'시작\s*[:：]\s*`?(\d{1,2}):(\d{2})')
CIRCLED = '①②③④⑤⑥⑦⑧⑨'


# ---------------------------------------------------------------- 입력 읽기
def parse_hhmm(text, label='시각'):
    """'HH:MM' → (h, m). 형식이 틀리면 ValueError(메시지에 값)."""
    m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', text or '')
    if not m or not (0 <= int(m.group(1)) <= 23 and 0 <= int(m.group(2)) <= 59):
        raise ValueError('%s 형식 오류: %r → HH:MM (예 09:30) 으로 적어 주세요' % (label, text))
    return int(m.group(1)), int(m.group(2))


def read_start(root):
    """TASK.md 머리 20줄에서 `시작: HH:MM` 을 찾는다. 없으면 None."""
    path = os.path.join(root, 'TASK.md')
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, line in enumerate(fh):
            if i >= 20:
                break
            m = START_PAT.search(line)
            if m:
                return '%02d:%02d' % (int(m.group(1)), int(m.group(2)))
    return None


def elapsed_minutes(start_hhmm, now):
    """오늘 start_hhmm 부터 now 까지 분(내림). 자정을 넘긴 경우(-12h 이하)는 하루를 더한다."""
    h, m = parse_hhmm(start_hhmm, '시작 시각')
    start = now.replace(hour=h, minute=m, second=0, microsecond=0)
    minutes = (now - start).total_seconds() / 60.0
    if minutes < -720:
        minutes += 1440
    return int(minutes // 1)


def _split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def read_rules(root):
    """PLAN.md '## 4' 절의 규칙표 → 상태 집계. 표가 없으면 found=False."""
    out = {'found': False, 'total': 0, 'pass': 0, 'fail': 0, 'not_run': 0, 'human_check': 0,
           'fail_names': [], 'not_run_names': []}
    path = os.path.join(root, 'PLAN.md')
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as fh:
        lines = fh.read().splitlines()
    in_sec, table = False, []
    for line in lines:
        if re.match(r'^##\s*4[.\s]', line):
            in_sec = True
            continue
        if in_sec and re.match(r'^##\s', line):
            break
        if in_sec and line.lstrip().startswith('|'):
            table.append(line)
    if len(table) < 2:
        return out
    header = _split_row(table[0])
    rule_idx = next((i for i, c in enumerate(header) if c == '규칙'), None)
    if rule_idx is None:
        rule_idx = next((i for i, c in enumerate(header) if '규칙' in c), None)
    if rule_idx is None:
        return out
    status_idx = next((i for i, c in enumerate(header) if '상태' in c), None)
    out['found'] = True
    for line in table[1:]:
        cells = _split_row(line)
        if all(re.match(r'^:?-+:?$', c or '-') for c in cells):
            continue  # 구분선
        if len(cells) <= rule_idx or not cells[rule_idx]:
            continue  # 템플릿 빈 행
        name = cells[rule_idx]
        if status_idx is not None and len(cells) > status_idx:
            probe = cells[status_idx]
        else:
            probe = ' '.join(cells)
        m = STATUS_PAT.search(probe)
        status = m.group(1) if m else 'NOT_RUN'
        out['total'] += 1
        if status == 'PASS':
            out['pass'] += 1
        elif status == 'FAIL':
            out['fail'] += 1
            out['fail_names'].append(name)
        elif status == 'HUMAN_CHECK':
            out['human_check'] += 1
        else:
            out['not_run'] += 1
            out['not_run_names'].append(name)
    return out


def read_tests(root, tests_arg=None):
    """--tests N/M 이 있으면 그것을, 없으면 out/debug/*/ 의 green.txt·red.txt 유무만 본다(테스트를 돌리지 않는다)."""
    out = {'source': 'none', 'pass': None, 'total': None, 'label': '', 'red_open': []}
    if tests_arg:
        m = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', tests_arg)
        if not m:
            raise ValueError('--tests 형식 오류: %r → N/M (예 5/7, PASS/전체) 으로 적어 주세요' % tests_arg)
        out.update(source='arg', **{'pass': int(m.group(1)), 'total': int(m.group(2))})
        out['label'] = '테스트 %d/%d' % (out['pass'], out['total'])
        return out
    stages = sorted(d for d in glob.glob(os.path.join(root, 'out', 'debug', '*')) if os.path.isdir(d))
    if not stages:
        return out
    green = [d for d in stages if os.path.exists(os.path.join(d, 'green.txt'))]
    out['red_open'] = [os.path.basename(d) for d in stages
                       if os.path.exists(os.path.join(d, 'red.txt')) and not os.path.exists(os.path.join(d, 'green.txt'))]
    out.update(source='debug', **{'pass': len(green), 'total': len(stages)})
    out['label'] = '디버그 단계 green %d/%d' % (len(green), len(stages))
    return out


def last_record_minutes(root, now=None):
    """out/debug 아래 가장 최근 파일의 수정 시각부터 지금까지 분. 파일이 없으면 None (시험장은 git 없음)."""
    base = os.path.join(root, 'out', 'debug')
    latest = None
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__',)]
        for fn in filenames:
            try:
                mt = os.path.getmtime(os.path.join(dirpath, fn))
            except OSError:
                continue
            latest = mt if latest is None else max(latest, mt)
    if latest is None:
        return None
    now_ts = (now or dt.datetime.now()).timestamp()
    return max(0, int((now_ts - latest) / 60))


# ---------------------------------------------------------------- 판단
def phase_key(a, b):
    return '%d' % a if b == 999 else '%d–%d' % (a, b)


def phase_tag(name):
    head = name.split(' — ')[0].strip()
    return head[0] if head and head[0] in CIRCLED else head


def current_phase(elapsed):
    """(key, name, from, until). 시작 전(음수)은 RUN.md '0' 행으로 본다."""
    if elapsed < 0:
        return '0', '시작 전 — 접속·사전 체험', None, 0
    name, until = phase_of(elapsed)
    for a, b, n in PHASES:
        if n == name:
            return phase_key(a, b), name, a, b
    return '170', name, 170, 999


def milestone(elapsed):
    for at, label in MILESTONES:
        if elapsed < at:
            return {'name': label, 'at': at, 'remain_min': at - elapsed}
    return {'name': '제출', 'at': 170, 'remain_min': 170 - elapsed}


def read_pending(root):
    """decisions/pending.md 의 미답 결정 ID 와 담당자 확인 필요 ID. 파일이 없으면 빈 목록."""
    path = os.path.join(root, 'decisions', 'pending.md')
    out = {'open': [], 'ask': []}
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    for block in re.split(r'(?m)^(?=## D\d+)', text):
        m = re.match(r'## (D\d+)\b(.*)', block)
        if not m or '(예시' in m.group(2):
            continue
        if re.search(r'(?m)^- \[[xX]\]', block):
            continue
        out['open'].append(m.group(1))
        if re.search(r'담당자 확인:\s*필요', m.group(2)):
            out['ask'].append(m.group(1))
    return out


def recommend(elapsed, key, rules, tests, record_age, pending=None):
    """추천 3개. 순서: 고정 (1) → 기록 경과 → 규칙 FAIL/NOT_RUN → 테스트·디버그 신호 → 구간 기본."""
    items = []

    def add(text):
        if text and text not in items:
            items.append(text)

    if 100 <= elapsed < 120:
        add(FIRST_FREEZE)
    elif elapsed >= 144:
        add(FINAL_FREEZE)
    if pending and pending['open']:
        ask = ' (담당자 확인 필요: %s)' % '·'.join(pending['ask']) if pending['ask'] else ''
        add('결정 대기 %s%s → decisions/pending.md 에 [x] 또는 decide.py(사람이 실행). 그 결정에 기대는 작업은 답 전까지 보류' % ('·'.join(pending['open']), ask))
    if record_age is not None and record_age > 20:
        add('기록: `python3 scripts/debug_dir.py NN_단계명` 폴더에 red/green/verify 남기기 (마지막 기록 %d분 전)' % record_age)
    elif record_age is None and elapsed >= 30:
        add('기록 없음 → `python3 scripts/debug_dir.py 01_첫완주` 로 첫 기록')
    if rules['fail_names'] or rules['not_run_names']:
        parts = []
        if rules['fail_names']:
            parts.append('규칙 "%s" FAIL 고치기' % rules['fail_names'][0])
        if rules['not_run_names']:
            parts.append('규칙 "%s" 테스트 실행(NOT_RUN → 먼저 FAIL 확인 → PASS → 발동 건수)' % rules['not_run_names'][0])
        add(' · '.join(parts))
    if tests['source'] == 'arg' and tests['pass'] < tests['total']:
        add('테스트 FAIL %d건 고치기(PASS %d/%d) → 통과 후 green.txt' % (tests['total'] - tests['pass'], tests['pass'], tests['total']))
    for stage in tests['red_open'][:1]:
        add('디버그 단계 %s: red.txt 만 있음 → PASS 확인 후 green.txt 남기기' % stage)
    for text in PHASE_TODO.get(key, PHASE_TODO['170']):
        add(text)
    return items[:3]


# ---------------------------------------------------------------- 조립
def build(root, start=None, now=None, tests_arg=None, use_records=True):
    """꼬리 3줄과 JSON 용 데이터를 만든다. start 가 None 이면 TASK.md 에서 읽고, 그래도 없으면 안내만 돌려준다."""
    if isinstance(now, str):
        h, m = parse_hhmm(now, '--now')
        now = dt.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    now = now or dt.datetime.now()
    start = start or read_start(root)
    if not start:
        return {'start': None, 'now': now.strftime('%H:%M'), 'message': NO_START_MSG,
                'lines': [NO_START_MSG, NO_START_HINT]}
    elapsed = elapsed_minutes(start, now)
    key, name, p_from, p_until = current_phase(elapsed)
    rules = read_rules(root)
    tests = read_tests(root, tests_arg)
    record_age = last_record_minutes(root, now) if use_records else None
    ms = milestone(elapsed)
    pending = read_pending(root)
    recs = recommend(elapsed, key, rules, tests, record_age, pending)
    waiting = WAITING.get(key, '')

    if not rules['found']:
        rules_text = '규칙표 없음'
    elif rules['total'] == 0:
        rules_text = '규칙표 미작성'
    else:
        rules_text = '규칙 %d/%d' % (rules['pass'], rules['total'])
    ms_text = ('%s까지 %d분' % (ms['name'], ms['remain_min']) if ms['remain_min'] >= 0
               else '%s 시각 %d분 지남' % (ms['name'], -ms['remain_min']))
    parts = ['지금: %s %s' % (phase_tag(name), rules_text), '경과 %d분' % elapsed, ms_text]
    if tests['label']:
        parts.append(tests['label'])
    parts.append('마지막 기록 %d분 전' % record_age if record_age is not None else '기록 없음')
    line1 = ' · '.join(parts)
    line2 = '다음 추천: ' + ' '.join('(%d) %s' % (i + 1, t) for i, t in enumerate(recs))
    if elapsed >= 80:
        line2 += ' ※ ' + NO_NEW_APPROACH
    line3 = '대기 중 할 일(사람): ' + (waiting or '—')
    return {
        'start': start, 'now': now.strftime('%H:%M'), 'elapsed_min': elapsed,
        'phase': {'key': key, 'name': name, 'tag': phase_tag(name), 'from': p_from, 'until': p_until},
        'milestone': ms, 'rules': rules, 'tests': tests, 'last_record_min': record_age, 'pending': pending,
        'no_new_approach': elapsed >= 80, 'recommendations': recs, 'waiting': waiting,
        'lines': [line1, line2, line3],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description='보고 꼬리 3줄: 지금 구간·규칙 진행·다음 추천 3개·대기 중 할 일 (AGENTS.md 7절)')
    ap.add_argument('--start', help='HH:MM 시작 시각 (없으면 TASK.md 머리의 `시작: HH:MM`)')
    ap.add_argument('--now', help='HH:MM 현재 시각 (재현·테스트용, 기본 지금)')
    ap.add_argument('--tests', help='unittest 결과 N/M (PASS/전체). 없으면 out/debug/*/green.txt 유무만 본다')
    ap.add_argument('--root', default=os.getcwd(), help='TASK.md·PLAN.md·out/ 이 있는 폴더 (기본 현재 폴더)')
    ap.add_argument('--json', action='store_true', help='같은 내용을 JSON 으로 출력')
    args = ap.parse_args(argv)
    try:
        if args.start:
            parse_hhmm(args.start, '--start')
        data = build(args.root, start=args.start, now=args.now, tests_arg=args.tests)
    except ValueError as e:
        sys.stderr.write('next.py: %s\n' % e)
        return 2
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for line in data['lines']:
            print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
