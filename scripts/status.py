#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""status.py — 지금 상태 1줄 (표준 라이브러리, Python 3.9). 시계는 숫자를 보여 줄 뿐 아무 판단도 하지 않는다.

사용:
  python3 scripts/status.py                 # 1줄
  python3 scripts/status.py --json          # 같은 내용을 JSON 한 줄로(보통 1KB 안팎 — 에이전트·대기 항목이 많으면 더 길다)
  python3 scripts/status.py --tests 24/24   # unittest 결과(PASS/전체)를 직접 알려줄 때만 '테스트 N/M' 이 붙는다
  python3 scripts/status.py --now 10:25     # 재현·테스트용 현재 시각
  python3 scripts/status.py --root DIR      # TASK.md·PLAN.md·PRD.md·out/·decisions/·work/ 가 있는 폴더(기본 현재 폴더)

출력 1줄(예):
  상태: ACTIVE · 남은 94분 · task 6/9 · 테스트 24/24 · debug green 7/10 · 대기 D07(담당자 D07) · A_core: 판정 04 구현 중 · B_web: 더미 렌더 완료 · PRD v1

입력(가벼운 읽기만, 테스트를 돌리지 않는다):
  TASK.md 머리 20줄의 Status: `ACTIVE` · 시작: HH:MM · 마감: HH:MM (마감이 없으면 '마감 미기록', 콜론은 빠져도 읽는다)
  PLAN.md '## 4' 절 표(헤더에 task 와 상태 열, 상태 단어 PASS/FAIL/NOT_RUN/HUMAN_CHECK) → task PASS/전체
    상태 칸이 '생략(사유)' 이면 전체에는 넣고 따로 센다 → 'task 8/9(생략 1)'
  out/debug/*/green.txt|red.txt → debug green N/M(폴더 수 기준)
  decisions/pending.md 의 `## Dnn` 중 고른 후보 줄(`- [x] A. …` · `- [x] 반영 HH:MM A. …`)이 없는 항목 → 대기 ID
    ('담당자 확인: 필요' 는 괄호 안, 제목에 '(예시' 가 든 항목은 뺀다) — decide.py 의 미답 판정과 같은 규칙
  work/agents/*.md 머리 `상태:` 줄 → 에이전트별 한 줄(_template.md 제외)
  work/agents/*.md ⑦ 절의 `연결 N`(보낸 담당 = 파일 첫 글자 A/B/C) · 각 파일 어디든 `연결 N 반영`(받은 담당) · PLAN.md '## 4-2' 표의 받는 담당
    → 아직 안 받은 담당이 있으면 '연결 대기 1(→B·C)·6(→C)' (없으면 이 칸은 아예 없다. 받는 담당이 사람인 행과 PLAN 행이 없는 번호 '(→?)' 는 표시만)
  work/agents/*.md ⑦ 절의 `@A C1: …`(받는 담당 글자 + 보낸 글자·번호) · 어느 파일이든 `C1 반영`·`C1 해결` → 닫히지 않은 것만 '요청 대기 C1(→A)'
    (번호 없는 `@A:` 줄과 `@사람` 은 세지 않는다)
  PRD.md 머리 5줄의 `버전: `vN`` → 줄 끝 'PRD v1'(파일이 없으면 'PRD 없음', 버전 줄이 없으면 'PRD 버전 미기록')
없는 것: 어떤 추천·독촉·유도 문구도 내지 않는다. 남은 분은 표시일 뿐 분기 기준이 아니다.
exit 0: 항상(시작·마감·파일이 없어도) / exit 2: 인자 형식 오류(--now·--tests)
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

STATUS_WORD_PAT = re.compile(r'\b(PASS|FAIL|NOT_RUN|HUMAN_CHECK)\b')
TASK_STATUS_PAT = re.compile(r'Status\s*[:：]\s*`?([A-Za-z_]+)`?')
START_PAT = re.compile(r'시작\s*[:：]?\s*`?(\d{1,2}):(\d{2})')
DEADLINE_PAT = re.compile(r'마감\s*[:：]?\s*`?(\d{1,2}):(\d{2})')
# 답한 항목 = 고른 후보 줄이 있음. decide.py CAND_RE 의 체크된 후보와 같은 모양(`- [x] A.` / `- [x] 반영 HH:MM A.`)만 센다
ANSWERED_PAT = re.compile(r'(?m)^- \[[xX]\]\s*(?:반영\s*\d\d:\d\d\s*)?[A-Za-z0-9][.)]')
SKIPPED_WORD = '생략'
CP_PAT = re.compile(r'\bCP\s*[:：]\s*`?([^\s·`]+)')
AGENT_STATUS_PAT = re.compile(r'^\s*상태\s*[:：]\s*(.*?)\s*$')
AGENT_UPDATED_TAIL = re.compile(r'\s*·\s*갱신\s*[:：]?\s*\S*\s*$')
PRD_VERSION_PAT = re.compile(r'버전\s*[:：]\s*`?\s*([vV]\d+(?:\.\d+)*)')
# 연결 신호: ⑦ 의 `연결 1` · `연결 #: 1` · `연결 1:` (숫자가 없는 템플릿 줄 `연결 #: <번호>` 는 안 잡힌다) / 받은 쪽의 `연결 1 반영`
SIGNAL_PAT = re.compile(r'연결\s*#?\s*[:：]?\s*(\d+)(?!\s*반영)')
APPLIED_PAT = re.compile(r'연결\s*#?\s*[:：]?\s*(\d+)\s*반영')
SECTION7_PAT = re.compile(r'^##\s*⑦')
# 요청: ⑦ 의 `@A C1: 내용`(받는 담당 A, 보낸 C 의 1번) / 닫힘 표시 `C1 반영`(받은 쪽 ⑤) 또는 `C1 해결`(보낸 쪽)
REQUEST_PAT = re.compile(r'@([ABC])\s+([ABC]\d+)\s*[:：]\s*(.*)')
REQ_DONE_PAT = re.compile(r'(?<![A-Za-z0-9_])([ABC]\d+)\s*(?:반영|해결)')
REQ_TEXT_MAX = 80
RECEIVER_LETTER_PAT = re.compile(r'\b([ABC])\b')
LINK_ROW_MAX = 120
HEAD_LINES = 20
PRD_HEAD_LINES = 5
AGENT_TEXT_MAX = 40
MAX_IDS_SHOWN = 6
MAX_ASK_SHOWN = 3


# ---------------------------------------------------------------- 시각
def parse_hhmm(text, label='시각'):
    """'HH:MM' → (h, m). 형식이 틀리면 ValueError(메시지에 값)."""
    m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', text or '')
    if not m or not (0 <= int(m.group(1)) <= 23 and 0 <= int(m.group(2)) <= 59):
        raise ValueError('%s 형식 오류: %r → HH:MM (예 09:30) 으로 적어 주세요' % (label, text))
    return int(m.group(1)), int(m.group(2))


def minutes_from(hhmm, now):
    """오늘 hhmm 부터 now 까지 분(내림). 자정을 넘긴 경우(-12h 이하)는 하루를 더한다."""
    h, m = parse_hhmm(hhmm)
    at = now.replace(hour=h, minute=m, second=0, microsecond=0)
    minutes = (now - at).total_seconds() / 60.0
    if minutes < -720:
        minutes += 1440
    return int(minutes // 1)


def minutes_until(hhmm, now):
    """now 부터 오늘 hhmm 까지 분(내림). 자정 너머의 마감(-12h 이하)은 하루를 더한다. 지났으면 음수."""
    h, m = parse_hhmm(hhmm)
    at = now.replace(hour=h, minute=m, second=0, microsecond=0)
    minutes = (at - now).total_seconds() / 60.0
    if minutes < -720:
        minutes += 1440
    return int(minutes // 1)


# ---------------------------------------------------------------- 입력 읽기
def _read_lines(path, limit=None):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8', errors='replace') as fh:
        lines = []
        for i, line in enumerate(fh):
            if limit is not None and i >= limit:
                break
            lines.append(line.rstrip('\r\n'))
    return lines


def read_task_head(root):
    """TASK.md 머리 20줄 → {'status', 'start', 'deadline', 'cp'} (없는 값은 None). 파일이 없어도 같은 모양."""
    out = {'status': None, 'start': None, 'deadline': None, 'cp': None}
    lines = _read_lines(os.path.join(root, 'TASK.md'), HEAD_LINES)
    if lines is None:
        return out
    for line in lines:
        if out['status'] is None:
            m = TASK_STATUS_PAT.search(line)
            if m:
                out['status'] = m.group(1)
        if out['start'] is None:
            m = START_PAT.search(line)
            if m:
                out['start'] = '%02d:%02d' % (int(m.group(1)), int(m.group(2)))
        if out['deadline'] is None:
            m = DEADLINE_PAT.search(line)
            if m:
                out['deadline'] = '%02d:%02d' % (int(m.group(1)), int(m.group(2)))
        if out['cp'] is None:
            m = CP_PAT.search(line)
            if m and m.group(1) != '-':
                out['cp'] = m.group(1)
    return out


def _split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def _is_separator(cells):
    return all(re.match(r'^:?-+:?$', c or '-') for c in cells)


def read_tasks(root):
    """PLAN.md '## 4' 절의 task 표 → 상태 집계. 표가 없거나 task 열이 없으면 found=False.
    task 칸이 빈 행(템플릿)은 세지 않는다. 상태 칸에 상태 단어가 없으면 NOT_RUN 으로 센다.
    상태 칸이 '생략(사유)'(또는 'NOT_RUN(생략: …)')이면 skipped 로 센다 — 전체(total)에는 들어간다."""
    out = {'found': False, 'total': 0, 'pass': 0, 'fail': 0, 'not_run': 0, 'human_check': 0, 'skipped': 0}
    lines = _read_lines(os.path.join(root, 'PLAN.md'))
    if lines is None:
        return out
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
    header = [c.lower() for c in _split_row(table[0])]
    task_idx = next((i for i, c in enumerate(header) if c == 'task'), None)
    if task_idx is None:
        task_idx = next((i for i, c in enumerate(header) if 'task' in c), None)
    if task_idx is None:
        return out
    status_idx = next((i for i, c in enumerate(header) if '상태' in c), None)
    out['found'] = True
    for line in table[1:]:
        cells = _split_row(line)
        if _is_separator(cells):
            continue
        if len(cells) <= task_idx or not cells[task_idx]:
            continue
        probe = cells[status_idx] if (status_idx is not None and len(cells) > status_idx) else ''
        m = STATUS_WORD_PAT.search(probe)
        status = m.group(1) if m else 'NOT_RUN'
        out['total'] += 1
        if status == 'NOT_RUN' and SKIPPED_WORD in probe:
            out['skipped'] += 1
            continue
        key = {'PASS': 'pass', 'FAIL': 'fail', 'HUMAN_CHECK': 'human_check'}.get(status, 'not_run')
        out[key] += 1
    return out


def read_tests(tests_arg):
    """--tests N/M → {'pass': N, 'total': M}. 없으면 None. 형식이 틀리면 ValueError."""
    if not tests_arg:
        return None
    m = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', tests_arg)
    if not m:
        raise ValueError('--tests 형식 오류: %r → N/M (예 24/24, PASS/전체) 으로 적어 주세요' % tests_arg)
    return {'pass': int(m.group(1)), 'total': int(m.group(2))}


def read_debug(root):
    """out/debug/*/ 폴더의 green.txt·red.txt 유무만 본다(테스트를 돌리지 않는다)."""
    base = os.path.join(root, 'out', 'debug')
    out = {'exists': os.path.isdir(base), 'green': 0, 'total': 0, 'red_open': []}
    if not out['exists']:
        return out
    stages = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    for name in stages:
        d = os.path.join(base, name)
        has_green = os.path.exists(os.path.join(d, 'green.txt'))
        has_red = os.path.exists(os.path.join(d, 'red.txt'))
        out['total'] += 1
        if has_green:
            out['green'] += 1
        elif has_red:
            out['red_open'].append(name)
    return out


def read_pending(root):
    """decisions/pending.md 의 미답 결정 ID 와 '담당자 확인: 필요' ID. '(예시' 항목과 고른 후보 줄이 있는 항목은 뺀다.
    고른 후보 줄 = `- [x] A. …` 또는 `- [x] 반영 HH:MM A. …`(decide.py 와 같은 규칙). 후보 없이 따로 쓴 `[x] 반영 HH:MM` 줄은
    어느 후보를 골랐는지 없으므로 답으로 보지 않는다(decide.py 폼에도 미답으로 뜬다)."""
    out = {'open': [], 'ask': []}
    path = os.path.join(root, 'decisions', 'pending.md')
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    for block in re.split(r'(?m)^(?=## )', text):  # 다른 '## ' 절이 앞 항목에 섞이지 않게 모든 절 머리에서 자른다
        m = re.match(r'## (D\d+)\b(.*)', block)
        if not m or '(예시' in m.group(2):
            continue
        if ANSWERED_PAT.search(block):  # 고른 후보 줄이 하나라도 있으면 답한 항목(decide.py 와 같은 판정)
            continue
        out['open'].append(m.group(1))
        if re.search(r'담당자 확인\s*[:：]\s*필요', m.group(2)):
            out['ask'].append(m.group(1))
    return out


def read_agents(root):
    """work/agents/*.md 머리 3줄 안의 `상태: … · 갱신 HH:MM` → [(이름, 상태 한 줄)] 이름순. _로 시작하는 파일은 뺀다."""
    base = os.path.join(root, 'work', 'agents')
    out = []
    if not os.path.isdir(base):
        return out
    for fn in sorted(os.listdir(base)):
        if not fn.endswith('.md') or fn.startswith('_'):
            continue
        lines = _read_lines(os.path.join(base, fn), 3) or []
        text = ''
        for line in lines:
            m = AGENT_STATUS_PAT.match(line)
            if m:
                text = AGENT_UPDATED_TAIL.sub('', m.group(1)).strip()
                break
        if text:
            out.append((fn[:-3], text[:AGENT_TEXT_MAX]))
    return out


def read_links(root):
    """PLAN.md '## 4-2' 연결 표 → {번호: {'to': [받는 담당 글자 A/B/C], 'row': 행 요약}}. 표가 없으면 {}.
    받는 담당 칸의 A·B·C 만 센다('사람' 은 받은 표시를 남길 수 없으므로 대기로 세지 않는다)."""
    out = {}
    lines = _read_lines(os.path.join(root, 'PLAN.md'))
    if lines is None:
        return out
    in_sec, table = False, []
    for line in lines:
        if re.match(r'^##\s*4-2\b', line):
            in_sec = True
            continue
        if in_sec and re.match(r'^##\s', line):
            break
        if in_sec and line.lstrip().startswith('|'):
            table.append(line)
    if len(table) < 2:
        return out
    header = _split_row(table[0])
    to_idx = next((i for i, c in enumerate(header) if '받는' in c), None)
    if to_idx is None:
        return out
    for line in table[1:]:
        cells = _split_row(line)
        if _is_separator(cells) or not cells or not re.match(r'^\d+$', cells[0]):
            continue
        receivers = RECEIVER_LETTER_PAT.findall(cells[to_idx]) if len(cells) > to_idx else []
        out[cells[0]] = {'to': sorted(set(receivers)), 'row': ' | '.join(cells[1:])[:LINK_ROW_MAX]}
    return out


def read_signals(root):
    """work/agents/*.md ⑦ 의 `연결 N` → 보낸 담당(파일 첫 글자), 각 파일 어디든 `연결 N 반영` → 받은 담당.
    PLAN 4-2 의 받는 담당 중 보낸 쪽도 아니고 반영 표시도 없는 담당이 남으면 pending 에 {'n', 'from', 'to'}.
    PLAN 행이 없는 번호는 to=['?']. 받는 담당이 사람뿐인 행은 pending 에 들어가지 않는다.
    ⑦ 의 `@A C1: 내용` 은 requests 에 {'id', 'from', 'to', 'text'} — 어느 파일에든 `C1 반영`·`C1 해결` 이 있으면 닫힌 것."""
    base = os.path.join(root, 'work', 'agents')
    sent, applied, requests, done = {}, {}, [], set()
    if os.path.isdir(base):
        for fn in sorted(os.listdir(base)):
            if not fn.endswith('.md') or fn.startswith('_'):
                continue
            letter = fn[0].upper()
            lines = _read_lines(os.path.join(base, fn)) or []
            text = '\n'.join(lines)
            for m in APPLIED_PAT.finditer(text):
                applied.setdefault(m.group(1), set()).add(letter)
            for m in REQ_DONE_PAT.finditer(text):
                done.add(m.group(1))
            sec, in7 = [], False
            for line in lines:
                if SECTION7_PAT.match(line):
                    in7 = True
                    continue
                if in7 and re.match(r'^##\s', line):
                    break
                if in7:
                    sec.append(line)
            for m in SIGNAL_PAT.finditer('\n'.join(sec)):
                sent.setdefault(m.group(1), set()).add(letter)
            for line in sec:
                m = REQUEST_PAT.search(line)
                if m and m.group(1) != letter:
                    requests.append({'id': m.group(2), 'from': letter, 'to': m.group(1), 'text': m.group(3).strip()[:REQ_TEXT_MAX]})
    links = read_links(root)
    pending = []
    for n in sorted(sent, key=int):
        link = links.get(n)
        if link is None:
            waiting = ['?']
        else:
            waiting = [r for r in link['to'] if r not in sent[n] and r not in applied.get(n, set())]
        if waiting:
            pending.append({'n': n, 'from': sorted(sent[n]), 'to': waiting, 'row': (link or {}).get('row', '')})
    open_requests = [r for r in requests if r['id'] not in done]
    return {'sent': {n: sorted(v) for n, v in sent.items()}, 'pending': pending, 'requests': open_requests}


def signals_text(signals):
    """'연결 대기 1(→B·C)·6(→C)' — pending 이 없으면 ''(칸을 만들지 않는다)."""
    if not signals['pending']:
        return ''
    items = ['%s(→%s)' % (p['n'], '·'.join(p['to'])) for p in signals['pending'][:MAX_IDS_SHOWN]]
    text = '연결 대기 ' + '·'.join(items)
    if len(signals['pending']) > MAX_IDS_SHOWN:
        text += '+%d' % (len(signals['pending']) - MAX_IDS_SHOWN)
    return text


def requests_text(signals):
    """'요청 대기 C1(→A)·C2(→B)' — 닫히지 않은 요청이 없으면 ''."""
    reqs = signals.get('requests') or []
    if not reqs:
        return ''
    items = ['%s(→%s)' % (r['id'], r['to']) for r in reqs[:MAX_IDS_SHOWN]]
    text = '요청 대기 ' + '·'.join(items)
    if len(reqs) > MAX_IDS_SHOWN:
        text += '+%d' % (len(reqs) - MAX_IDS_SHOWN)
    return text


def read_prd(root):
    """PRD.md 머리 5줄의 `버전: `vN`` → 'v1'·'v1.1'(소문자). 파일이 없으면 None, 버전 줄이 없으면 ''."""
    lines = _read_lines(os.path.join(root, 'PRD.md'), PRD_HEAD_LINES)
    if lines is None:
        return None
    for line in lines:
        m = PRD_VERSION_PAT.search(line)
        if m:
            return m.group(1).lower()
    return ''


# ---------------------------------------------------------------- 조립
def _ids_text(ids, limit):
    shown = '·'.join(ids[:limit])
    if len(ids) > limit:
        shown += '+%d' % (len(ids) - limit)
    return shown


def pending_text(pending):
    if not pending['open']:
        return '대기 없음'
    text = '대기 ' + _ids_text(pending['open'], MAX_IDS_SHOWN)
    if pending['ask']:
        text += '(담당자 %s)' % _ids_text(pending['ask'], MAX_ASK_SHOWN)
    return text


def prd_text(version):
    if version is None:
        return 'PRD 없음'
    return ('PRD %s' % version) if version else 'PRD 버전 미기록'


def build(root, now=None, tests_arg=None):
    """1줄과 JSON 용 데이터를 만든다. now 는 datetime 또는 'HH:MM'(없으면 지금)."""
    if isinstance(now, str):
        h, m = parse_hhmm(now, '--now')
        now = dt.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    now = now or dt.datetime.now()
    head = read_task_head(root)
    tasks = read_tasks(root)
    tests = read_tests(tests_arg)
    debug = read_debug(root)
    pending = read_pending(root)
    agents = read_agents(root)
    signals = read_signals(root)
    prd = read_prd(root)
    elapsed = minutes_from(head['start'], now) if head['start'] else None
    remaining = minutes_until(head['deadline'], now) if head['deadline'] else None

    parts = ['상태: %s' % (head['status'] or '미기록')]
    if remaining is None:
        parts.append('마감 미기록')
    elif remaining >= 0:
        parts.append('남은 %d분' % remaining)
    else:
        parts.append('마감 지남 %d분' % -remaining)
    if tasks['found']:
        parts.append('task %d/%d%s' % (tasks['pass'], tasks['total'], ('(생략 %d)' % tasks['skipped']) if tasks['skipped'] else ''))
    else:
        parts.append('task 표 없음')
    if tests:
        parts.append('테스트 %d/%d' % (tests['pass'], tests['total']))
    parts.append('debug green %d/%d' % (debug['green'], debug['total']) if debug['total'] else 'debug 기록 없음')
    parts.append(pending_text(pending))
    if signals['pending']:
        parts.append(signals_text(signals))
    if signals['requests']:
        parts.append(requests_text(signals))
    for name, text in agents:
        parts.append('%s: %s' % (name, text))
    parts.append(prd_text(prd))
    line = ' · '.join(parts)
    return {
        'status': head['status'], 'start': head['start'], 'deadline': head['deadline'], 'cp': head['cp'],
        'now': now.strftime('%H:%M'), 'elapsed_min': elapsed, 'remaining_min': remaining,
        'tasks': tasks, 'tests': tests,
        'debug': {'green': debug['green'], 'total': debug['total'], 'red_open': debug['red_open'][:6]},
        'pending': {'open': pending['open'][:12], 'ask': pending['ask'][:12],
                    'open_n': len(pending['open']), 'ask_n': len(pending['ask'])},
        'agents': dict(agents),
        'signals': {'pending': [{'n': p['n'], 'from': p['from'], 'to': p['to']} for p in signals['pending'][:12]],
                    'pending_n': len(signals['pending'])},
        'requests': {'open': [{'id': r['id'], 'from': r['from'], 'to': r['to']} for r in signals['requests'][:12]],
                     'open_n': len(signals['requests'])},
        'prd': prd,
        'line': line,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description='지금 상태 1줄 (TASK·PLAN·out/debug·pending·work/agents·PRD 를 읽기만 한다)')
    ap.add_argument('--json', action='store_true', help='같은 내용을 JSON 한 줄로')
    ap.add_argument('--tests', help='unittest 결과 N/M (PASS/전체). 있을 때만 줄에 붙는다')
    ap.add_argument('--now', help='HH:MM 현재 시각 (재현·테스트용, 기본 지금)')
    ap.add_argument('--root', default=os.getcwd(), help='TASK.md·PLAN.md·PRD.md·out/·decisions/·work/ 가 있는 폴더 (기본 현재 폴더)')
    args = ap.parse_args(argv)
    try:
        data = build(args.root, now=args.now, tests_arg=args.tests)
    except ValueError as e:
        sys.stderr.write('status.py: %s\n' % e)
        return 2
    if args.json:
        print(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    else:
        print(data['line'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
